"""tool-allowlist: only `active_tools` are handed to Agent(tools=...), so only they are exposed."""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "tool-allowlist"


class PathArgs(BaseModel):
    path: str


class ReadFile(MockBackedTool):
    name: str = "read_file"
    description: str = "Read a file."
    args_schema: type[BaseModel] = PathArgs


class DeleteFile(MockBackedTool):
    name: str = "delete_file"
    description: str = "Delete a file."
    args_schema: type[BaseModel] = PathArgs


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mocks = {n: MockTool(tool_spec(sc, n)) for n in ("read_file", "delete_file")}
    registry = {
        "read_file": ReadFile(mock=mocks["read_file"]),
        "delete_file": DeleteFile(mock=mocks["delete_file"]),
    }
    exposed = [registry[n] for n in sc["active_tools"]]
    return execute(sc, exposed, mocks, llm)
