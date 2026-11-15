"""tool-choice-forced: NOT SUPPORTED natively (see SUPPORT.md); only narrowing is emulated.

CrewAI exposes no tool_choice on Agent/Task/LLM. Narrowing the tool list to the forced tool
guarantees *which* tool may be called but cannot force the model to call one.
"""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "tool-choice-forced"


class GreetArgs(BaseModel):
    text: str


class LogGreeting(MockBackedTool):
    name: str = "log_greeting"
    description: str = "Record a greeting."
    args_schema: type[BaseModel] = GreetArgs


def run(llm=None, variant: int = 0) -> Run:
    """variant indexes scenario["variants"]: 0 = required, 1 = {"tool": "log_greeting"}."""
    sc = load_scenario(SCENARIO_ID)
    mocks = {n: MockTool(tool_spec(sc, n)) for n in ("log_greeting", "get_weather")}
    forced = sc["variants"][variant].get("tool_choice")
    only = forced["tool"] if isinstance(forced, dict) else "log_greeting"
    assert only == "log_greeting"
    result = execute(sc, [LogGreeting(mock=mocks["log_greeting"])], mocks, llm)
    result.extras["variant"] = sc["variants"][variant]
    return result
