"""tool-choice-none: EMULATED. CrewAI has no tool_choice option; the tool is simply not exposed."""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "tool-choice-none"


class WeatherArgs(BaseModel):
    city: str


class GetWeather(MockBackedTool):
    name: str = "get_weather"
    description: str = "Get current weather for a city."
    args_schema: type[BaseModel] = WeatherArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "get_weather"))
    defined = GetWeather(mock=mock)  # defined, but deliberately not passed to the Agent
    result = execute(sc, [], {"get_weather": mock}, llm)
    result.extras["defined_but_hidden"] = [defined.name]
    return result
