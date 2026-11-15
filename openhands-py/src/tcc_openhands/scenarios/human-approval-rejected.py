"""Approval denied: confirmation policy pauses, the user rejects, the tool never runs.

Same mechanism as ``approval-gated-action`` (security analyzer + ``ConfirmRisky`` +
``reject_pending_actions``); the rejection is recorded as ``UserRejectObservation`` and fed back.
"""

from __future__ import annotations

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "human-approval-rejected"
SCENARIO = load_scenario(ID)


def run(real: bool = False, variant: str | None = None) -> RunResult:  # noqa: ARG001
    trace = Trace()
    return run_scenario(
        SCENARIO,
        llm=build_llm(SCENARIO, trace, real=real),
        trace=trace,
        approval=SCENARIO["approval"],
    )


def check(result: RunResult, variant: str | None = None) -> list[str]:  # noqa: ARG001
    bad = check_expect(SCENARIO, result)
    if not result.paused_for_confirmation:
        bad.append("conversation never paused for confirmation")
    if result.rejected != 1:
        bad.append(f"expected 1 UserRejectObservation, got {result.rejected}")
    return bad
