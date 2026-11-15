"""Shared harness: scenario loading, scripted stub LLM, mock tool results, event capture, runner."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, Task
from crewai.events import crewai_event_bus
from crewai.events.types.llm_events import (
    LLMCallCompletedEvent,
    LLMCallType,
    LLMStreamChunkEvent,
)
from crewai.events.types.tool_usage_events import (
    ToolUsageErrorEvent,
    ToolUsageFinishedEvent,
    ToolUsageStartedEvent,
)
from crewai.hooks import HookAborted, InterceptionPoint, ToolCallHookContext, on, unregister_hook
from crewai.llms.base_llm import BaseLLM, llm_call_context
from crewai.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "scenarios"


def load_scenario(scenario_id: str) -> dict[str, Any]:
    return json.loads((SCENARIOS_DIR / f"{scenario_id}.json").read_text())


def tool_spec(scenario: dict[str, Any], name: str) -> dict[str, Any]:
    return next(t for t in scenario["tools"] if t["name"] == name)


class ToolFailed(RuntimeError):
    """Raised by a mock tool whose spec has `mock_error`."""


@dataclass
class MockTool:
    """Resolves a tool spec's mock_* fields; records every body execution in `executed`."""

    spec: dict[str, Any]
    executed: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, **args: Any) -> str:
        self.executed.append(args)
        spec = self.spec
        if "mock_error" in spec:
            raise ToolFailed(spec["mock_error"]["message"])
        if "mock_result_by_args" in spec:
            for value in args.values():
                if str(value) in spec["mock_result_by_args"]:
                    return json.dumps(spec["mock_result_by_args"][str(value)])
            raise ToolFailed(f"no mock result for {args}")
        if "mock_result_sequence" in spec:
            seq = spec["mock_result_sequence"]
            return json.dumps(seq[min(len(self.executed) - 1, len(seq) - 1)])
        return json.dumps(spec.get("mock_result"))


class MockBackedTool(BaseTool):
    """BaseTool delegating to a `MockTool`; subclasses set name, description, args_schema."""

    _mock: MockTool = PrivateAttr()

    def __init__(self, mock: MockTool, **data: Any) -> None:
        super().__init__(**data)
        self._mock = mock

    def _run(self, **kwargs: Any) -> Any:
        return self._mock(**kwargs)


class ScriptedLLM(BaseLLM):
    """Keyless stub LLM replaying a scenario's `mock_llm_script`.

    Subclasses CrewAI's public `BaseLLM`; advertising `supports_function_calling` makes the
    executor use the native tool-calling path, so a tool-call turn is returned as a list of
    OpenAI-shaped tool calls and a text turn as `str` (the same shapes native providers return).
    It emits the same stream/completed events native providers do. When the script is exhausted
    it returns `fallback_text` and counts the extra call in `overflow_calls`.
    """

    llm_type: str = "scripted"
    script: list[dict[str, Any]] = []
    fallback_text: str = "Final answer (forced)."
    calls: list[dict[str, Any]] = []
    overflow_calls: int = 0
    emit_stream: bool = False

    def supports_function_calling(self) -> bool:
        return True

    def supports_stop_words(self) -> bool:
        return False

    def call(  # type: ignore[override]
        self,
        messages: Any,
        tools: Any = None,
        callbacks: Any = None,
        available_functions: Any = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> Any:
        with llm_call_context():
            self._emit_call_started_event(
                messages=messages, tools=tools, from_task=from_task, from_agent=from_agent
            )
            return self._reply(messages, tools, from_task, from_agent)

    def _reply(self, messages: Any, tools: Any, from_task: Any, from_agent: Any) -> Any:
        offered = [t["function"]["name"] for t in tools or []]
        self.calls.append({"tools": offered, "n_messages": len(messages)})
        index = len(self.calls) - 1
        if index >= len(self.script):
            self.overflow_calls += 1
            turn: dict[str, Any] = {"finish_reason": "stop", "text": self.fallback_text}
        else:
            turn = self.script[index]
        if turn.get("tool_calls"):
            response: Any = [
                {
                    "id": f"call_{index}_{i}",
                    "type": "function",
                    "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])},
                }
                for i, c in enumerate(turn["tool_calls"])
            ]
        else:
            response = turn.get("text", "")
            if self.emit_stream:
                for word in response.split(" "):
                    self._emit_stream_chunk_event(
                        chunk=word + " ",
                        from_task=from_task,
                        from_agent=from_agent,
                        call_type=LLMCallType.LLM_CALL,
                    )
        self._emit_call_completed_event(
            response=response,
            call_type=LLMCallType.TOOL_CALL if isinstance(response, list) else LLMCallType.LLM_CALL,
            from_task=from_task,
            from_agent=from_agent,
            messages=messages,
            finish_reason=turn.get("finish_reason"),
        )
        return response


def scripted_llm(scenario: dict[str, Any], **overrides: Any) -> ScriptedLLM:
    params: dict[str, Any] = {
        "model": "scripted",
        "script": scenario.get("mock_llm_script", []),
        "calls": [],
    }
    max_tokens = scenario.get("limits", {}).get("max_output_tokens")
    if max_tokens:
        params["max_tokens"] = max_tokens
    params.update(overrides)
    return ScriptedLLM(**params)


@dataclass
class Observed:
    """What a run did, reconstructed from the CrewAI event bus (ordered by emission_sequence)."""

    output: Any = None
    error: BaseException | None = None
    events: list[tuple[str, Any]] = field(default_factory=list)

    def kinds(self) -> list[str]:
        return [k for k, _ in self.events]

    def attempted(self) -> list[tuple[str, dict[str, Any]]]:
        return [(e.tool_name, e.tool_args) for k, e in self.events if k == "tool-call"]

    def results(self) -> list[Any]:
        return [e for k, e in self.events if k == "tool-result"]

    def tool_errors(self) -> list[Any]:
        return [e for k, e in self.events if k == "tool-error"]

    def finish_reasons(self) -> list[str | None]:
        return [e.finish_reason for k, e in self.events if k in ("finish", "llm-tool-turn")]

    def event_order(self) -> list[str]:
        """Event kinds with consecutive duplicates collapsed (text-delta bursts)."""
        out: list[str] = []
        for kind in self.kinds():
            if kind != "llm-tool-turn" and (not out or out[-1] != kind):
                out.append(kind)
        return out

    @property
    def raw(self) -> str:
        return getattr(self.output, "raw", "") or ""


def run_agent(
    llm: BaseLLM,
    tools: Iterable[Any],
    prompt: str,
    *,
    max_iter: int = 10,
    max_execution_time: int | None = 60,
    output_pydantic: type[BaseModel] | None = None,
    human_input: bool = False,
    reraise: bool = False,
    before_run: Callable[[], None] | None = None,
) -> Observed:
    """Run one Agent/Task via Crew.kickoff and collect tool/LLM events."""
    captured: list[tuple[str, Any]] = []
    obs = Observed()
    with crewai_event_bus.scoped_handlers():

        def on(event_type: type, label: str) -> None:
            @crewai_event_bus.on(event_type)
            def _handler(source: Any, event: Any) -> None:
                captured.append((label, event))

        on(ToolUsageStartedEvent, "tool-call")
        on(ToolUsageFinishedEvent, "tool-result")
        on(ToolUsageErrorEvent, "tool-error")
        on(LLMStreamChunkEvent, "text-delta")

        @crewai_event_bus.on(LLMCallCompletedEvent)
        def _completed(source: Any, event: Any) -> None:
            # A completed call that returned tool calls is a tool turn, not the run's finish.
            captured.append(
                ("llm-tool-turn" if event.call_type == LLMCallType.TOOL_CALL else "finish", event)
            )

        agent = Agent(
            role="Assistant",
            goal="Complete the user's request using the available tools.",
            backstory="A careful assistant.",
            llm=llm,
            tools=list(tools),
            max_iter=max_iter,
            max_execution_time=max_execution_time,
            cache=False,  # identical repeated calls must really execute (stuck-loop/max-steps)
            allow_delegation=False,
            verbose=False,
        )
        task = Task(
            description=prompt,
            expected_output="A short answer to the request.",
            agent=agent,
            output_pydantic=output_pydantic,
            human_input=human_input,
        )
        if before_run:
            before_run()
        try:
            obs.output = Crew(agents=[agent], tasks=[task], verbose=False).kickoff()
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller/tests
            if reraise:
                raise
            obs.error = exc
        crewai_event_bus.flush()
    captured.sort(key=lambda item: item[1].emission_sequence or 0)
    obs.events = captured
    return obs


@dataclass
class Run:
    """Everything a scenario run produced, for tests and the CLI runner."""

    scenario: dict[str, Any]
    obs: Observed
    mocks: dict[str, MockTool]
    llm: BaseLLM
    extras: dict[str, Any] = field(default_factory=dict)

    def executed(self, name: str) -> list[dict[str, Any]]:
        return self.mocks[name].executed


def execute(
    scenario: dict[str, Any],
    tools: list[Any],
    mocks: dict[str, MockTool],
    llm: BaseLLM | None,
    *,
    script: list[dict[str, Any]] | None = None,
    **run_kwargs: Any,
) -> Run:
    """Run `scenario["prompt"]` with a real `llm`, or a scripted stub when `llm` is None."""
    if llm is None:
        extra = {"script": script} if script is not None else {}
        llm = scripted_llm(scenario, **extra)
    obs = run_agent(llm, tools, scenario["prompt"], **run_kwargs)
    return Run(scenario, obs, mocks, llm)


@contextmanager
def approval_gate(
    tool_names: list[str], approve: Callable[[str, dict[str, Any]], bool] | None = None
) -> Iterator[list[tuple[str, dict[str, Any], bool]]]:
    """Per-tool-call approval via a global PRE_TOOL_CALL hook (CrewAI "tool call hooks").

    A denied call raises `HookAborted`: the tool body is skipped and the model receives
    "Tool execution blocked by hook. Tool: <name>". With `approve=None` the operator is asked
    on stdin through `ctx.request_human_input`; tests inject a callable instead.
    Yields the decision log `[(tool, args, approved)]`.
    """
    decisions: list[tuple[str, dict[str, Any], bool]] = []

    @on(InterceptionPoint.PRE_TOOL_CALL, tools=tool_names)
    def gate(ctx: ToolCallHookContext) -> None:
        args = dict(ctx.tool_input)
        if approve is None:
            answer = ctx.request_human_input(
                prompt=f"Approve {ctx.tool_name}?",
                default_message=f"Input: {args}\nType 'yes' to approve:",
            )
            ok = answer.strip().lower() == "yes"
        else:
            ok = approve(ctx.tool_name, args)
        decisions.append((ctx.tool_name, args, ok))
        if not ok:
            raise HookAborted(reason="denied by operator", source="approval-gate")

    try:
        yield decisions
    finally:
        unregister_hook(InterceptionPoint.PRE_TOOL_CALL, gate)
