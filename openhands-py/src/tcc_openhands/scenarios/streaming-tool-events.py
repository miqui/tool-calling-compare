"""Streaming: ``LLM(stream=True)`` + ``token_callbacks`` + event callback give ordered events.

Order observed: tool-call (ActionEvent), tool-result (ObservationEvent), text-delta (token
callback chunks), finish (conversation status FINISHED).
"""

from __future__ import annotations

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "streaming-tool-events"
SCENARIO = load_scenario(ID)


def run(real: bool = False, variant: str | None = None) -> RunResult:  # noqa: ARG001
    trace = Trace()
    llm = build_llm(SCENARIO, trace, real=real, stream=True)
    return run_scenario(SCENARIO, llm=llm, trace=trace, streaming=True)


def check(result: RunResult, variant: str | None = None) -> list[str]:  # noqa: ARG001
    return check_expect(SCENARIO, result)
