"""max-steps-exceeded: Agent(max_iter=limits.max_steps) caps the tool loop."""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "max-steps-exceeded"


class NoArgs(BaseModel):
    pass


class CheckQueue(MockBackedTool):
    name: str = "check_queue"
    description: str = "Return queue length."
    args_schema: type[BaseModel] = NoArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "check_queue"))
    return execute(
        sc,
        [CheckQueue(mock=mock)],
        {"check_queue": mock},
        llm,
        max_iter=sc["limits"]["max_steps"],
    )
