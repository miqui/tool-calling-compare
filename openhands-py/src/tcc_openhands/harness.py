"""Shared plumbing: scenario loading, JSON-spec -> OpenHands tools, scripted/real LLMs, run loop.

Everything here uses the real ``openhands.sdk`` (Agent, Conversation, Tool, ToolDefinition,
Action/Observation/ToolExecutor, callbacks, confirmation policy, security analyzer, stuck
detection, ``max_iteration_per_run``). Only the LLM can be swapped for a scripted one.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openhands.sdk import (
    LLM,
    Action,
    Agent,
    Conversation,
    Event,
    Message,
    Observation,
    TextContent,
    Tool,
    ToolDefinition,
)
from openhands.sdk.conversation.state import ConversationExecutionStatus
from openhands.sdk.conversation.types import StuckDetectionThresholds
from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    MessageEvent,
    ObservationEvent,
    UserRejectObservation,
)
from openhands.sdk.event.conversation_error import ConversationErrorEvent
from openhands.sdk.llm import MessageToolCall
from openhands.sdk.security.analyzer import SecurityAnalyzerBase
from openhands.sdk.security.confirmation_policy import ConfirmRisky
from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.testing import TestLLM
from openhands.sdk.tool import ToolExecutor, register_tool
from pydantic import Field, SecretStr, create_model

SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "scenarios"
DEFAULT_MODEL = "openrouter/anthropic/claude-sonnet-4.5"


def load_scenario(scenario_id: str) -> dict[str, Any]:
    return json.loads((SCENARIOS_DIR / f"{scenario_id}.json").read_text())


# --------------------------------------------------------------------------- tools


class MockObservation(Observation):
    """Generic observation: the mock result serialised as JSON text."""


_PY_TYPES: dict[str, type] = {"string": str, "integer": int, "number": float, "boolean": bool}


def action_type_for(tool: dict[str, Any]) -> type[Action]:
    """Build a pydantic ``Action`` from a scenario tool's ``parameters`` (legacy or JSON Schema)."""
    params = tool["parameters"]
    if params.get("type") == "object":
        props = params.get("properties", {})
        required = set(params.get("required", []))
    else:  # legacy: {name: type-string}
        props = {k: {"type": v} for k, v in params.items()}
        required = set(params)
    fields: dict[str, Any] = {}
    for name, spec in props.items():
        py = _PY_TYPES[spec.get("type", "string")]
        kwargs: dict[str, Any] = {"description": spec.get("description", name)}
        if "minimum" in spec:
            kwargs["ge"] = spec["minimum"]
        if name in required:
            fields[name] = (py, Field(..., **kwargs))
        else:
            fields[name] = (py | None, Field(None, **kwargs))
    return create_model(f"{tool['name']}_action", __base__=Action, **fields)


@dataclass
class Trace:
    """What the LLM asked for vs. what executors actually ran."""

    attempted: list[dict[str, Any]] = field(default_factory=list)
    executed: list[dict[str, Any]] = field(default_factory=list)
    finish_reasons: list[str] = field(default_factory=list)
    exposed_tools: list[str] = field(default_factory=list)
    completion_kwargs: list[dict[str, Any]] = field(default_factory=list)
    llm_calls: int = 0


class MockExecutor(ToolExecutor[Any, MockObservation]):
    """Deterministic executor driven by the scenario's mock_* keys."""

    def __init__(self, spec: dict[str, Any], trace: Trace, *, raise_errors: bool = False):
        self.spec = spec
        self.trace = trace
        self.raise_errors = raise_errors
        self._seq = 0

    def __call__(self, action: Any, conversation: Any = None) -> MockObservation:  # noqa: ARG002
        args = action.model_dump(exclude_none=True)
        args.pop("kind", None)
        args.pop("security_risk", None)
        args.pop("summary", None)
        self.trace.executed.append({"name": self.spec["name"], "arguments": args})
        if "mock_error" in self.spec:
            msg = self.spec["mock_error"]["message"]
            if self.raise_errors:
                raise RuntimeError(msg)  # SDK turns any executor exception into AgentErrorEvent
            return MockObservation.from_text(f"Error: {msg}", is_error=True)
        if "mock_result_by_args" in self.spec:
            key = str(next(iter(args.values()), ""))
            result = self.spec["mock_result_by_args"].get(key, {"error": f"no mock for {key}"})
        elif "mock_result_sequence" in self.spec:
            seq = self.spec["mock_result_sequence"]
            result = seq[min(self._seq, len(seq) - 1)]
            self._seq += 1
        else:
            result = self.spec.get("mock_result")
        return MockObservation.from_text(json.dumps(result))


_TOOL_CLASSES: dict[str, type[ToolDefinition]] = {}


def _tool_class(name: str) -> type[ToolDefinition]:
    """``ToolDefinition.name`` is a ClassVar, so each tool name needs its own subclass."""
    if name not in _TOOL_CLASSES:

        def create(cls: Any, *_a: Any, **_k: Any) -> Any:
            raise NotImplementedError("instances are registered directly with register_tool")

        _TOOL_CLASSES[name] = type(
            f"Mock_{name}_Tool", (ToolDefinition,), {"name": name, "create": classmethod(create)}
        )
    return _TOOL_CLASSES[name]


def make_tool(spec: dict[str, Any], trace: Trace, *, raise_errors: bool = False) -> ToolDefinition:
    return _tool_class(spec["name"])(
        name=spec["name"],
        description=spec.get("description") or spec["name"],
        action_type=action_type_for(spec),
        observation_type=MockObservation,
        executor=MockExecutor(spec, trace, raise_errors=raise_errors),
    )


def register_scenario_tools(
    scenario: dict[str, Any], trace: Trace, *, raise_errors: bool = False
) -> list[Tool]:
    """Register every tool in the scenario with the SDK registry and return ``Tool`` specs."""
    specs: list[Tool] = []
    for t in scenario["tools"]:
        register_tool(t["name"], make_tool(t, trace, raise_errors=raise_errors))
        specs.append(Tool(name=t["name"]))
    return specs


class ToolNameRiskAnalyzer(SecurityAnalyzerBase):
    """Security analyzer: tools flagged ``requires_approval`` are HIGH risk, the rest LOW."""

    high_risk_tools: list[str] = Field(default_factory=list)

    def security_risk(self, action: ActionEvent) -> SecurityRisk:
        return SecurityRisk.HIGH if action.tool_name in self.high_risk_tools else SecurityRisk.LOW


# --------------------------------------------------------------------------- LLMs


def script_to_messages(script: Sequence[dict[str, Any]]) -> list[Message]:
    msgs: list[Message] = []
    for i, turn in enumerate(script):
        calls = [
            MessageToolCall(
                id=f"call_{i}_{j}",
                name=c["name"],
                arguments=json.dumps(c["arguments"]),
                origin="completion",
            )
            for j, c in enumerate(turn.get("tool_calls", []))
        ]
        msgs.append(
            Message(
                role="assistant",
                content=[TextContent(text=turn.get("text", ""))],
                tool_calls=calls or None,
            )
        )
    return msgs


def _record(trace: Trace, resp: Any, tools: Any, kwargs: dict[str, Any]) -> None:
    trace.llm_calls += 1
    trace.exposed_tools = [t.name for t in (tools or [])]
    trace.completion_kwargs.append(dict(kwargs))
    for tc in resp.message.tool_calls or []:
        try:
            args = json.loads(tc.arguments)
        except json.JSONDecodeError:
            args = {"_raw": tc.arguments}
        trace.attempted.append({"name": tc.name, "arguments": args})
    fr = None
    raw = getattr(resp, "raw_response", None)
    if raw is not None and getattr(raw, "choices", None):
        fr = raw.choices[0].finish_reason
    trace.finish_reasons.append(fr or "unknown")


class ScriptedLLM(TestLLM):
    """``openhands.sdk.testing.TestLLM`` that also follows ``mock_llm_script`` finish reasons,
    streams text through ``on_token`` and records what the agent sent (tools, tool_choice)."""

    __test__ = False
    trace: Any = Field(default=None, exclude=True)
    tool_choice: Any = Field(default=None, exclude=True)
    turn_finish: list[str] = Field(default_factory=list, exclude=True)

    def completion(self, messages, tools=None, add_security_risk_prediction=False, **kwargs):  # type: ignore[override]
        on_token = kwargs.get("on_token")
        extra = dict(kwargs)
        extra.pop("on_token", None)
        if self.tool_choice is not None:
            extra["tool_choice"] = self.tool_choice
        idx = self._call_count
        resp = super().completion(
            messages, tools, add_security_risk_prediction=add_security_risk_prediction, **kwargs
        )
        if idx < len(self.turn_finish):
            resp.raw_response.choices[0].finish_reason = self.turn_finish[idx]
        if on_token is not None and resp.message.content:
            from litellm.types.utils import Delta, ModelResponseStream, StreamingChoices

            text = "".join(c.text for c in resp.message.content if isinstance(c, TextContent))
            for word in filter(None, text.split(" ")):
                on_token(
                    ModelResponseStream(
                        choices=[StreamingChoices(delta=Delta(content=word + " "), index=0)]
                    )
                )
        _record(self.trace, resp, tools, extra)
        return resp


class RealLLM(LLM):
    """Real ``LLM`` (via LiteLLM) that optionally forces ``tool_choice`` and records the trace.

    The SDK's Agent never sets ``tool_choice`` itself, so it is injected at the LLM boundary.
    """

    trace: Any = Field(default=None, exclude=True)
    tool_choice: Any = Field(default=None, exclude=True)

    def completion(self, messages, tools=None, add_security_risk_prediction=False, **kwargs):  # type: ignore[override]
        if self.tool_choice is not None:
            kwargs["tool_choice"] = self.tool_choice
        resp = super().completion(
            messages, tools, add_security_risk_prediction=add_security_risk_prediction, **kwargs
        )
        if self.trace is not None:
            _record(self.trace, resp, tools, {k: v for k, v in kwargs.items() if k != "on_token"})
        return resp


def scripted_llm(
    scenario: dict[str, Any], trace: Trace, tool_choice: Any = None, **llm_kwargs: Any
) -> ScriptedLLM:
    script = scenario.get("mock_llm_script") or default_script(scenario)
    llm = ScriptedLLM.from_messages(script_to_messages(script), usage_id="scripted", **llm_kwargs)
    llm.trace = trace
    llm.tool_choice = tool_choice
    llm.turn_finish = [t["finish_reason"] for t in script]
    return llm


def real_llm(trace: Trace, tool_choice: Any = None, **llm_kwargs: Any) -> RealLLM:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set (real-LLM runs are local only)")
    llm = RealLLM(
        usage_id="agent",
        model=os.environ.get("TCC_MODEL", DEFAULT_MODEL),
        api_key=SecretStr(key),
        temperature=0.0,
        **llm_kwargs,
    )
    llm.trace = trace
    llm.tool_choice = tool_choice
    return llm


def default_script(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Scripts for the four legacy scenarios, which carry no ``mock_llm_script``."""
    sid = scenario["id"]
    if sid == "weather-lookup":
        call = {"name": "get_weather", "arguments": {"city": "Paris"}}
        return [
            {"finish_reason": "tool_calls", "tool_calls": [call]},
            {"finish_reason": "stop", "text": "It is 18C and cloudy in Paris."},
        ]
    if sid == "file-write":
        call = {"name": "write_file", "arguments": {"path": "notes.txt", "content": "hello world"}}
        return [
            {"finish_reason": "tool_calls", "tool_calls": [call]},
            {"finish_reason": "stop", "text": "Created notes.txt."},
        ]
    if sid == "approval-gated-action":
        call = {"name": "delete_file", "arguments": {"path": "old-report.txt"}}
        return [
            {"finish_reason": "tool_calls", "tool_calls": [call]},
            {"finish_reason": "stop", "text": "Done."},
        ]
    if sid == "loop-stop-conditions":
        call = {"name": "poll_status", "arguments": {}}
        return [{"finish_reason": "tool_calls", "tool_calls": [call]}] * 3
    raise KeyError(f"no mock_llm_script for {sid}")


# --------------------------------------------------------------------------- run


@dataclass
class RunResult:
    scenario_id: str
    status: str
    events: list[Event]
    trace: Trace
    final_text: str | None
    stopped_by: str
    validation_errors: int = 0
    unknown_tool_errors: int = 0
    tool_errors: int = 0
    rejected: int = 0
    paused_for_confirmation: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def attempted_calls(self) -> list[dict[str, Any]]:
        return self.trace.attempted

    @property
    def executed_calls(self) -> list[dict[str, Any]]:
        return self.trace.executed

    @property
    def steps(self) -> int:
        return self.trace.llm_calls


def _final_text(events: list[Event]) -> str | None:
    for e in reversed(events):
        if isinstance(e, MessageEvent) and e.source == "agent":
            return "".join(
                c.text for c in e.llm_message.content if isinstance(c, TextContent)
            ).strip()
    return None


def summarize(
    scenario_id: str,
    conv: Any,
    events: list[Event],
    trace: Trace,
    *,
    paused: bool = False,
    stopped_override: str | None = None,
) -> RunResult:
    status = conv.state.execution_status
    status_v = status.value if hasattr(status, "value") else str(status)
    errors = [e for e in events if isinstance(e, AgentErrorEvent)]
    conv_errors = [e for e in events if isinstance(e, ConversationErrorEvent)]
    obs_err = [e for e in events if isinstance(e, ObservationEvent) and e.observation.is_error]
    if stopped_override:
        stopped = stopped_override
    elif any(c.code == "MaxIterationsReached" for c in conv_errors):
        stopped = "max_steps"
    elif status == ConversationExecutionStatus.STUCK:
        stopped = "stuck_detected"
    elif trace.finish_reasons and trace.finish_reasons[-1] == "length":
        stopped = "length"
    elif status == ConversationExecutionStatus.FINISHED:
        stopped = "final_answer"
    else:
        stopped = status_v
    return RunResult(
        scenario_id=scenario_id,
        status=status_v,
        events=events,
        trace=trace,
        final_text=_final_text(events),
        stopped_by=stopped,
        validation_errors=sum(1 for e in errors if e.validation_errors),
        unknown_tool_errors=sum(1 for e in errors if "not found" in e.error),
        tool_errors=len(obs_err)
        + sum(1 for e in errors if not e.validation_errors)
        - sum(1 for e in errors if "not found" in e.error),
        rejected=sum(1 for e in events if isinstance(e, UserRejectObservation)),
        paused_for_confirmation=paused,
    )


def run_scenario(
    scenario: dict[str, Any],
    *,
    llm: LLM | None = None,
    tool_choice: Any = None,
    agent_kwargs: dict[str, Any] | None = None,
    conversation_kwargs: dict[str, Any] | None = None,
    tools: list[Tool] | None = None,
    approval: str | None = None,
    raise_errors: bool = False,
    workspace: str | Path | None = None,
    on_event: Callable[[Event], None] | None = None,
    trace: Trace | None = None,
    stopped_override: str | None = None,
    streaming: bool = False,
    prompt: str | None = None,
) -> RunResult:
    """Run one scenario through Agent + Conversation and summarise what happened.

    ``llm`` defaults to a scripted LLM following ``mock_llm_script``.
    """
    trace = trace or Trace()
    tool_specs = tools or register_scenario_tools(scenario, trace, raise_errors=raise_errors)
    llm = llm or scripted_llm(scenario, trace, tool_choice)
    # Only our tools: no think/finish built-ins, so a plain assistant message ends the run
    # and the exposed tool set equals the scenario's.
    agent = Agent(
        llm=llm,
        tools=tool_specs,
        include_default_tools=[],
        **(agent_kwargs or {}),
    )
    events: list[Event] = []

    def cb(e: Event) -> None:
        events.append(e)
        if on_event:
            on_event(e)

    ckw = dict(conversation_kwargs or {})
    limits = scenario.get("limits", {})
    if "max_steps" in limits:
        ckw.setdefault("max_iteration_per_run", limits["max_steps"])
    if "repeat_threshold" in limits:
        ckw.setdefault(
            "stuck_detection_thresholds",
            StuckDetectionThresholds(action_observation=limits["repeat_threshold"]),
        )
    ws = workspace or tempfile.mkdtemp(prefix="tcc-oh-")
    token_cbs = [lambda chunk: cb_token(events, chunk)] if streaming else None
    conv = Conversation(
        agent=agent,
        workspace=str(ws),
        callbacks=[cb],
        token_callbacks=token_cbs,
        visualizer=None,
        **ckw,
    )
    paused = False
    try:
        if approval:
            high = [t["name"] for t in scenario["tools"] if t.get("requires_approval")]
            conv.set_security_analyzer(ToolNameRiskAnalyzer(high_risk_tools=high))
            conv.set_confirmation_policy(
                ConfirmRisky(threshold=SecurityRisk.HIGH, confirm_unknown=False)
            )
        conv.send_message(prompt or scenario["prompt"])
        conv.run()
        if approval and conv.state.execution_status == (
            ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
        ):
            paused = True
            if approval == "deny":
                conv.reject_pending_actions("User denied the action")
            conv.run()
        return summarize(
            scenario["id"], conv, events, trace, paused=paused, stopped_override=stopped_override
        )
    finally:
        conv.close()


def cb_token(events: list[Event], chunk: Any) -> None:
    """Token callback: record a marker event name per streamed text delta."""
    try:
        text = chunk.choices[0].delta.content
    except (AttributeError, IndexError):
        text = None
    if text:
        events.append(_TextDelta(text))


class _TextDelta:
    """Not an SDK Event: lightweight marker kept in the event list for ordering checks."""

    def __init__(self, text: str) -> None:
        self.text = text
