"""human-approval-rejected: PRE_TOOL_CALL hook raises HookAborted; tool body never runs.

Note: Task(human_input=True) is NOT used here. It asks a human to review the agent's *final
answer*, not individual tool calls (see SUPPORT.md).
"""

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

SCENARIO_ID = "human-approval-rejected"


class TransferArgs(BaseModel):
    account: str
    amount: float


class TransferFunds(MockBackedTool):
    name: str = "transfer_funds"
    description: str = "Transfer money."
    args_schema: type[BaseModel] = TransferArgs


def run(llm=None, approve=None) -> Run:
    """Default: the operator denies. Real llm with approve=None prompts on stdin."""
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "transfer_funds"))
    decide = approve if approve is not None else (lambda _n, _a: False)
    if llm is not None and approve is None:
        decide = None
    with approval_gate(["transfer_funds"], decide) as decisions:
        result = execute(sc, [TransferFunds(mock=mock)], {"transfer_funds": mock}, llm)
    result.extras["decisions"] = decisions
    return result
