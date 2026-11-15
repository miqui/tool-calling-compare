"""tool-throws-error: tool body raises; CrewAI feeds the error back and the loop continues."""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "tool-throws-error"


class FetchArgs(BaseModel):
    url: str


class FetchUrl(MockBackedTool):
    name: str = "fetch_url"
    description: str = "Fetch a URL."
    args_schema: type[BaseModel] = FetchArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "fetch_url"))
    return execute(sc, [FetchUrl(mock=mock)], {"fetch_url": mock}, llm)
