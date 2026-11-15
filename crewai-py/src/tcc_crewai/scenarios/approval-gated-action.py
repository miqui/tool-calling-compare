"""approval-gated-action (legacy): destructive tool behind a PRE_TOOL_CALL approval hook."""

from pydantic import BaseModel

from tcc_crewai.common import (
    MockBackedTool,
    MockTool,
    Run,
    approval_gate,
    execute,
    load_scenario,
    tool_spec,
)

SCENARIO_ID = "approval-gated-action"


class DeleteArgs(BaseModel):
    path: str


class DeleteFile(MockBackedTool):
    name: str = "delete_file"
    description: str = "Delete a file."
    args_schema: type[BaseModel] = DeleteArgs


def script(variant: str) -> list[dict]:
    final = (
        "Deleted old-report.txt."
        if variant == "approve"
        else "The deletion was denied, so old-report.txt was not deleted."
    )
    return [
        {
            "finish_reason": "tool_calls",
            "tool_calls": [{"name": "delete_file", "arguments": {"path": "old-report.txt"}}],
        },
        {"finish_reason": "stop", "text": final},
    ]


def run(llm=None, variant: str = "deny", approve=None) -> Run:
    """variant: "approve" | "deny". `approve=None` + real llm asks the operator on stdin."""
    sc = load_scenario(SCENARIO_ID)
    spec = dict(tool_spec(sc, "delete_file"), mock_result={"deleted": True})
    mock = MockTool(spec)
    decide = approve if approve is not None else (lambda _n, _a: variant == "approve")
    if llm is not None and approve is None:
        decide = None  # real run: ask a human
    with approval_gate(["delete_file"], decide) as decisions:
        result = execute(
            sc, [DeleteFile(mock=mock)], {"delete_file": mock}, llm, script=script(variant)
        )
    result.extras["decisions"] = decisions
    return result
