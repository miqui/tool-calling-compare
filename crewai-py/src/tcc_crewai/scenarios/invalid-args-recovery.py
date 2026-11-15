"""invalid-args-recovery: args_schema rejects minutes="five"; error is fed back, model retries."""

from pydantic import BaseModel, Field

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "invalid-args-recovery"


class TimerArgs(BaseModel):
    minutes: int = Field(ge=1)


class SetTimer(MockBackedTool):
    name: str = "set_timer"
    description: str = "Set a timer."
    args_schema: type[BaseModel] = TimerArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "set_timer"))
    return execute(sc, [SetTimer(mock=mock)], {"set_timer": mock}, llm)
