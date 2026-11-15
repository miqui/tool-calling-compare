"""max-output-tokens-truncation: LLM(max_tokens=limits.max_output_tokens); finish_reason=length."""

from pydantic import BaseModel

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "max-output-tokens-truncation"


class WriteArgs(BaseModel):
    path: str
    content: str


class WriteFile(MockBackedTool):
    name: str = "write_file"
    description: str = "Write a file."
    args_schema: type[BaseModel] = WriteArgs


def real_llm_params(sc: dict) -> dict:
    """Extra `LLM(...)` kwargs for a real model run."""
    return {"max_tokens": sc["limits"]["max_output_tokens"]}


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "write_file"))
    return execute(sc, [WriteFile(mock=mock)], {"write_file": mock}, llm)
