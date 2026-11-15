"""tool_choice=none: tools are registered but the model is told not to call them.

Injected at the LLM boundary (the Agent has no tool_choice option); see ``tool-choice-forced``.
"""

from __future__ import annotations

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "tool-choice-none"
SCENARIO = load_scenario(ID)


def run(real: bool = False, variant: str | None = None) -> RunResult:  # noqa: ARG001
    trace = Trace()
    llm = build_llm(SCENARIO, trace, real=real, tool_choice=SCENARIO["tool_choice"])
    return run_scenario(SCENARIO, llm=llm, trace=trace)


def check(result: RunResult, variant: str | None = None) -> list[str]:  # noqa: ARG001
    bad = check_expect(SCENARIO, result)
    kwargs = result.trace.completion_kwargs
    if not kwargs or kwargs[0].get("tool_choice") != "none":
        bad.append("tool_choice=none not sent to completion")
    if result.executed_calls:
        bad.append("a tool was executed")
    return bad
