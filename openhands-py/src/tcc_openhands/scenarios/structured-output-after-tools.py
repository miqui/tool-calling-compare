"""Tools first, then a schema-constrained final answer.

PARTIAL: the SDK has no native structured final output for ``Agent`` runs, so the final assistant
message is parsed as JSON and validated against ``output_schema`` by the harness. For a real LLM
the schema is added to the prompt.
"""

from __future__ import annotations

import json

from tcc_openhands.checks import build_llm, check_expect, validate_schema
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "structured-output-after-tools"
SCENARIO = load_scenario(ID)


def run(real: bool = False, variant: str | None = None) -> RunResult:  # noqa: ARG001
    trace = Trace()
    prompt = (
        SCENARIO["prompt"]
        + " Reply with ONLY a JSON object matching this schema: "
        + json.dumps(SCENARIO["output_schema"])
    )
    result = run_scenario(
        SCENARIO, llm=build_llm(SCENARIO, trace, real=real), trace=trace, prompt=prompt
    )
    try:
        text = (result.final_text or "").strip().removeprefix("```json").strip("`\n ")
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    result.extra["schema_errors"] = (
        validate_schema(value, SCENARIO["output_schema"]) if value is not None else ["not JSON"]
    )
    result.extra["final_output"] = value
    return result


def check(result: RunResult, variant: str | None = None) -> list[str]:  # noqa: ARG001
    return check_expect(SCENARIO, result) + list(result.extra["schema_errors"])
