"""weather-lookup (legacy): @tool-decorated function, one call, answer uses the result."""

from crewai.tools import tool

from tcc_crewai.common import MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "weather-lookup"
# Legacy scenario has no mock_llm_script; this one is derived from its `expect`.
SCRIPT = [
    {
        "finish_reason": "tool_calls",
        "tool_calls": [{"name": "get_weather", "arguments": {"city": "Paris"}}],
    },
    {"finish_reason": "stop", "text": "It is 18C and cloudy in Paris."},
]


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "get_weather"))

    @tool("get_weather")
    def get_weather(city: str) -> str:
        """Get current weather for a city."""
        return mock(city=city)

    return execute(sc, [get_weather], {"get_weather": mock}, llm, script=SCRIPT)
