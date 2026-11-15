"""parallel-tool-calls: two independent calls in ONE assistant turn (native tool-call batch)."""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "parallel-tool-calls"


class WeatherArgs(BaseModel):
    city: str


class GetWeather(MockBackedTool):
    name: str = "get_weather"
    description: str = "Get current weather for a city."
    args_schema: type[BaseModel] = WeatherArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "get_weather"))
    return execute(sc, [GetWeather(mock=mock)], {"get_weather": mock}, llm)
