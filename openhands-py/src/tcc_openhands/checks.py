"""Assertions shared by unit tests and the real-LLM runner."""

from __future__ import annotations

import json
from typing import Any

from openhands.sdk import LLM
from openhands.sdk.event import ActionEvent, ObservationEvent

from tcc_openhands.harness import RunResult, Trace, _TextDelta, real_llm, scripted_llm


def build_llm(
    scenario: dict[str, Any],
    trace: Trace,
    *,
    real: bool = False,
    tool_choice: Any = None,
    **llm_kwargs: Any,
) -> LLM:
    """Scripted LLM by default; a real OpenRouter-backed LLM when ``real`` is true."""
    if real:
        return real_llm(trace, tool_choice, **llm_kwargs)
    return scripted_llm(scenario, trace, tool_choice, **llm_kwargs)


def validate_schema(value: Any, schema: dict[str, Any]) -> list[str]:
    """Tiny JSON-Schema subset validator (object/properties/required/additionalProperties)."""
    if schema.get("type") != "object":
        return []
    if not isinstance(value, dict):
        return ["not an object"]
    types: dict[str, Any] = {"string": str, "number": (int, float), "integer": int}
    errs = [f"missing {k}" for k in schema.get("required", []) if k not in value]
    props = schema.get("properties", {})
    for k, v in value.items():
        if k not in props:
            if schema.get("additionalProperties") is False:
                errs.append(f"unexpected {k}")
            continue
        t = types.get(props[k].get("type"))
        if t and (not isinstance(v, t) or isinstance(v, bool)):
            errs.append(f"{k}: wrong type")
    return errs


def event_order(result: RunResult) -> list[str]:
    """Collapse the event list into the scenario's streaming vocabulary."""
    out: list[str] = []
    for e in result.events:
        if isinstance(e, ActionEvent):
            name = "tool-call"
        elif isinstance(e, ObservationEvent):
            name = "tool-result"
        elif isinstance(e, _TextDelta):
            name = "text-delta"
        else:
            continue
        if not out or out[-1] != name:
            out.append(name)
    if result.status == "finished":
        out.append("finish")
    return out


def _key(c: dict[str, Any]) -> str:
    return json.dumps(c, sort_keys=True)


def check_expect(
    scenario: dict[str, Any], r: RunResult, expect: dict[str, Any] | None = None
) -> list[str]:
    """Compare a run with the scenario's ``expect`` block; returns a list of mismatches."""
    exp = expect if expect is not None else scenario.get("expect", {})
    bad: list[str] = []
    if "tool_calls" in exp:
        want = [_key(c) for c in exp["tool_calls"]]
        got = [_key(c) for c in r.attempted_calls]
        if exp.get("tool_calls_ordering") == "unordered":
            want, got = sorted(want), sorted(got)
        if want != got:
            bad.append(f"tool_calls: want {want} got {got}")
    if "executed_tool_calls" in exp:
        want = [_key(c) for c in exp["executed_tool_calls"]]
        if want != [_key(c) for c in r.executed_calls]:
            bad.append(f"executed: want {want} got {r.executed_calls}")
    if "tool_call_count" in exp and len(r.attempted_calls) != exp["tool_call_count"]:
        bad.append(f"tool_call_count {len(r.attempted_calls)} != {exp['tool_call_count']}")
    if "steps" in exp and r.steps != exp["steps"]:
        bad.append(f"steps {r.steps} != {exp['steps']}")
    if "stopped_by" in exp and r.stopped_by != exp["stopped_by"]:
        bad.append(f"stopped_by {r.stopped_by} != {exp['stopped_by']}")
    for s in exp.get("final_answer_contains", []):
        if s not in (r.final_text or ""):
            bad.append(f"final answer lacks {s!r}: {r.final_text!r}")
    for k in ("validation_errors", "unknown_tool_errors", "tool_errors"):
        if k in exp and getattr(r, k) != exp[k]:
            bad.append(f"{k} {getattr(r, k)} != {exp[k]}")
    if "tools_exposed" in exp and r.trace.exposed_tools != exp["tools_exposed"]:
        bad.append(f"tools_exposed {r.trace.exposed_tools} != {exp['tools_exposed']}")
    if "event_order" in exp and event_order(r) != exp["event_order"]:
        bad.append(f"event_order {event_order(r)} != {exp['event_order']}")
    if "final_output" in exp and r.extra.get("final_output") != exp["final_output"]:
        bad.append(f"final_output {r.extra.get('final_output')} != {exp['final_output']}")
    if exp.get("partial_tool_call_executed") is False and r.executed_calls:
        bad.append("partial tool call was executed")
    if exp.get("final_answer_mentions_denial") and "den" not in (r.final_text or "").lower():
        bad.append(f"final answer does not mention denial: {r.final_text!r}")
    return bad
