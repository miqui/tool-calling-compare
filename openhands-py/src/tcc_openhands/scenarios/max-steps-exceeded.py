"""Loop cap: ``Conversation(max_iteration_per_run=3)`` stops the run with MaxIterationsReached."""

from __future__ import annotations

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "max-steps-exceeded"
SCENARIO = load_scenario(ID)


def run(real: bool = False, variant: str | None = None) -> RunResult:  # noqa: ARG001
    trace = Trace()
    # run_scenario maps limits.max_steps -> max_iteration_per_run
    return run_scenario(SCENARIO, llm=build_llm(SCENARIO, trace, real=real), trace=trace)


def check(result: RunResult, variant: str | None = None) -> list[str]:  # noqa: ARG001
    return check_expect(SCENARIO, result)
