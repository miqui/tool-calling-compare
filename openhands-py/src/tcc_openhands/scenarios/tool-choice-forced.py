"""tool_choice forced (``required`` / a specific tool).

The SDK's Agent has no tool_choice option; it is injected at the LLM boundary
(``RealLLM`` / ``ScriptedLLM.tool_choice`` -> ``completion(tool_choice=...)`` -> LiteLLM).
"""

from __future__ import annotations

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "tool-choice-forced"
SCENARIO = load_scenario(ID)
VARIANTS = ["required", "tool"]


def _choice(variant: str | None) -> object:
    if variant == "tool":
        return {"type": "function", "function": {"name": "log_greeting"}}
    return "required"


def run(real: bool = False, variant: str | None = "required") -> RunResult:
    trace = Trace()
    choice = _choice(variant)
    result = run_scenario(
        SCENARIO, llm=build_llm(SCENARIO, trace, real=real, tool_choice=choice), trace=trace
    )
    result.extra["tool_choice"] = choice
    return result


def check(result: RunResult, variant: str | None = "required") -> list[str]:
    bad = check_expect(SCENARIO, result)
    kwargs = result.trace.completion_kwargs
    if not kwargs or kwargs[0].get("tool_choice") != _choice(variant):
        bad.append(f"tool_choice not sent to completion: {kwargs[:1]}")
    return bad
