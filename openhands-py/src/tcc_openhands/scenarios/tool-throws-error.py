"""Executor failure becomes an error result for the model; the loop continues.

Variants:
  ``observation`` (default) - executor catches the failure, returns ``is_error=True`` (idiomatic).
  ``raises``                - executor raises RuntimeError; the Agent makes an AgentErrorEvent.
"""

from __future__ import annotations

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "tool-throws-error"
SCENARIO = load_scenario(ID)
VARIANTS = ["observation", "raises"]


def run(real: bool = False, variant: str | None = None) -> RunResult:
    trace = Trace()
    return run_scenario(
        SCENARIO,
        llm=build_llm(SCENARIO, trace, real=real),
        trace=trace,
        raise_errors=variant == "raises",
    )


def check(result: RunResult, variant: str | None = None) -> list[str]:  # noqa: ARG001
    return check_expect(SCENARIO, result)
