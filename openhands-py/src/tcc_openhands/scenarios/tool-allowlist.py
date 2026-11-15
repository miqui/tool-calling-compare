"""Tool allowlist: register all tools, expose only ``active_tools`` (``filter_tools_regex``)."""

from __future__ import annotations

import re

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "tool-allowlist"
SCENARIO = load_scenario(ID)


def run(real: bool = False, variant: str | None = None) -> RunResult:  # noqa: ARG001
    trace = Trace()
    regex = "^(" + "|".join(re.escape(n) for n in SCENARIO["active_tools"]) + ")$"
    return run_scenario(
        SCENARIO,
        llm=build_llm(SCENARIO, trace, real=real),
        trace=trace,
        agent_kwargs={"filter_tools_regex": regex},
    )


def check(result: RunResult, variant: str | None = None) -> list[str]:  # noqa: ARG001
    return check_expect(SCENARIO, result)
