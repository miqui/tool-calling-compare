"""Output truncated (finish_reason=length) mid tool-call JSON.

PARTIAL: the SDK ignores ``finish_reason``; a truncated text-only turn just ends the run as
FINISHED. We cap output with ``LLM(max_output_tokens=...)`` and observe the finish reason on the
LLM response; ``stopped_by="length"`` comes from that observation, not from the SDK.
"""

from __future__ import annotations

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "max-output-tokens-truncation"
SCENARIO = load_scenario(ID)


def run(real: bool = False, variant: str | None = None) -> RunResult:  # noqa: ARG001
    trace = Trace()
    llm = build_llm(
        SCENARIO, trace, real=real, max_output_tokens=SCENARIO["limits"]["max_output_tokens"]
    )
    return run_scenario(SCENARIO, llm=llm, trace=trace)


def check(result: RunResult, variant: str | None = None) -> list[str]:  # noqa: ARG001
    return check_expect(SCENARIO, result)
