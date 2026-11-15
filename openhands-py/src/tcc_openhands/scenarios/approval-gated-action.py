"""Destructive tool gated by confirmation policy + security analyzer; run approved and denied.

``ToolNameRiskAnalyzer`` (a ``SecurityAnalyzerBase``) rates ``requires_approval`` tools HIGH;
``ConfirmRisky(threshold=HIGH)`` pauses the conversation (WAITING_FOR_CONFIRMATION). Approve ->
``conversation.run()`` again; deny -> ``conversation.reject_pending_actions()``.
"""

from __future__ import annotations

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "approval-gated-action"
SCENARIO = load_scenario(ID)
VARIANTS = ["approve", "deny"]


def run(real: bool = False, variant: str | None = "approve") -> RunResult:
    variant = variant or "approve"
    trace = Trace()
    scenario = SCENARIO
    if variant == "deny":  # model acknowledges the denial instead of claiming success
        script = [
            {
                "finish_reason": "tool_calls",
                "tool_calls": [{"name": "delete_file", "arguments": {"path": "old-report.txt"}}],
            },
            {"finish_reason": "stop", "text": "The deletion was denied, so nothing was removed."},
        ]
        scenario = {**SCENARIO, "mock_llm_script": script}
    scenario = {
        **scenario,
        "tools": [{**t, "mock_result": {"ok": True}} for t in SCENARIO["tools"]],
    }
    return run_scenario(
        scenario, llm=build_llm(scenario, trace, real=real), trace=trace, approval=variant
    )


def check(result: RunResult, variant: str | None = "approve") -> list[str]:
    spec = next(v for v in SCENARIO["variants"] if v["approval"] == (variant or "approve"))
    bad = []
    if not result.paused_for_confirmation:
        bad.append("conversation never paused for confirmation")
    executed = bool(result.executed_calls)
    if executed != spec["expect"]["tool_executed"]:
        bad.append(f"tool_executed={executed}")
    if spec["expect"].get("final_answer_mentions_denial"):
        bad += check_expect(SCENARIO, result, {"final_answer_mentions_denial": True})
    return bad
