"""loop-stop-conditions (legacy): poll_status never reports done; max_iter=3 stops the loop."""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "loop-stop-conditions"
SCRIPT = [
    {"finish_reason": "tool_calls", "tool_calls": [{"name": "poll_status", "arguments": {}}]}
    for _ in range(3)
]


class NoArgs(BaseModel):
    pass


class PollStatus(MockBackedTool):
    name: str = "poll_status"
    description: str = "Poll the job status."
    args_schema: type[BaseModel] = NoArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "poll_status"))
    return execute(
        sc,
        [PollStatus(mock=mock)],
        {"poll_status": mock},
        llm,
        script=SCRIPT,
        max_iter=sc["limits"]["max_steps"],
    )
