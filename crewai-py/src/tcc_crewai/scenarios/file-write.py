"""file-write (legacy): real write_file tool confined to a sandbox directory."""

import tempfile
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

from tcc_crewai.common import MockTool, Run, execute, load_scenario

SCENARIO_ID = "file-write"
SCRIPT = [
    {
        "finish_reason": "tool_calls",
        "tool_calls": [
            {"name": "write_file", "arguments": {"path": "notes.txt", "content": "hello world"}}
        ],
    },
    {"finish_reason": "stop", "text": "Created notes.txt."},
]


class WriteArgs(BaseModel):
    path: str
    content: str


class WriteFile(BaseTool):
    name: str = "write_file"
    description: str = "Write text content to a file inside the sandbox directory."
    args_schema: type[BaseModel] = WriteArgs
    _root: Path = PrivateAttr()
    _log: MockTool = PrivateAttr()

    def __init__(self, root: Path, log: MockTool, **data) -> None:
        super().__init__(**data)
        self._root = root.resolve()
        self._log = log

    def _run(self, path: str, content: str) -> str:
        target = (self._root / path).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("path escapes the sandbox")
        self._log.executed.append({"path": path, "content": content})
        target.write_text(content)
        return f"wrote {path}"


def run(llm=None, sandbox: Path | None = None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    root = sandbox or Path(tempfile.mkdtemp(prefix="tcc-crewai-"))
    log = MockTool({"name": "write_file"})
    result = execute(sc, [WriteFile(root=root, log=log)], {"write_file": log}, llm, script=SCRIPT)
    result.extras["sandbox"] = root
    return result
