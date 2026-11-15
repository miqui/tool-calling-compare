"""structured-output-after-tools: Task(output_pydantic=Weather) after a tool call."""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "structured-output-after-tools"


class WeatherArgs(BaseModel):
    city: str


class Weather(BaseModel):
    """Mirror of the scenario's output_schema (city: string, temp_c: number)."""

    city: str
    temp_c: float


class GetWeather(MockBackedTool):
    name: str = "get_weather"
    description: str = "Get current weather for a city."
    args_schema: type[BaseModel] = WeatherArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "get_weather"))
    return execute(sc, [GetWeather(mock=mock)], {"get_weather": mock}, llm, output_pydantic=Weather)
