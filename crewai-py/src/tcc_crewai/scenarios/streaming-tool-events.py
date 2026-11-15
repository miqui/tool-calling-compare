"""streaming-tool-events: ordered tool-call / tool-result / text-delta / finish from the event bus.

Mapping: ToolUsageStartedEvent=tool-call, ToolUsageFinishedEvent=tool-result,
LLMStreamChunkEvent=text-delta, LLMCallCompletedEvent (text)=finish. Real providers emit chunk
events when `LLM(stream=True)`; the keyless stub emits them itself (`emit_stream=True`).
"""

from pydantic import BaseModel

from tcc_crewai.common import (
    MockBackedTool,
    MockTool,
    Run,
    execute,
    load_scenario,
    scripted_llm,
    tool_spec,
)

SCENARIO_ID = "streaming-tool-events"


class WeatherArgs(BaseModel):
    city: str


class GetWeather(MockBackedTool):
    name: str = "get_weather"
    description: str = "Get current weather for a city."
    args_schema: type[BaseModel] = WeatherArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "get_weather"))
    if llm is None:
        llm = scripted_llm(sc, emit_stream=True)
    return execute(sc, [GetWeather(mock=mock)], {"get_weather": mock}, llm)
