"""Model writes a file inside a sandbox directory.

Default: hand-written ``write_file`` tool using the Action / Observation / ToolExecutor pattern.
Variant ``file-editor``: the SDK's built-in ``FileEditorTool`` (``file_editor`` create command).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from openhands.sdk import Action, Observation, Tool, ToolDefinition
from openhands.sdk.tool import ToolExecutor, register_tool
from openhands.tools.file_editor import FileEditorTool
from pydantic import Field

from tcc_openhands.checks import build_llm, check_expect
from tcc_openhands.harness import RunResult, Trace, load_scenario, run_scenario

ID = "file-write"
SCENARIO = load_scenario(ID)
VARIANTS = ["custom", "file-editor"]


class WriteFileAction(Action):
    path: str = Field(description="File path relative to the sandbox")
    content: str = Field(description="Text to write")


class WriteFileObservation(Observation):
    """Plain text observation (``Observation.from_text``)."""


class WriteFileExecutor(ToolExecutor[WriteFileAction, WriteFileObservation]):
    def __init__(self, sandbox: Path, trace: Trace) -> None:
        self.sandbox = sandbox.resolve()
        self.trace = trace

    def __call__(
        self,
        action: WriteFileAction,
        conversation: Any = None,  # noqa: ARG002
    ) -> WriteFileObservation:
        target = (self.sandbox / action.path).resolve()
        if not target.is_relative_to(self.sandbox):
            return WriteFileObservation.from_text("path escapes sandbox", is_error=True)
        target.write_text(action.content)
        self.trace.executed.append(
            {"name": "write_file", "arguments": {"path": action.path, "content": action.content}}
        )
        return WriteFileObservation.from_text(f"wrote {len(action.content)} bytes to {action.path}")


class WriteFileTool(ToolDefinition[WriteFileAction, WriteFileObservation]):
    @classmethod
    def create(cls, *_a: Any, **_k: Any) -> Any:
        raise NotImplementedError("registered as an instance")


def run(real: bool = False, variant: str | None = None) -> RunResult:
    sandbox = Path(tempfile.mkdtemp(prefix="tcc-oh-fw-"))
    trace = Trace()
    if variant == "file-editor":
        target = sandbox / "notes.txt"
        scenario = {
            **SCENARIO,
            "mock_llm_script": [
                {
                    "finish_reason": "tool_calls",
                    "tool_calls": [
                        {
                            "name": FileEditorTool.name,
                            "arguments": {
                                "command": "create",
                                "path": str(target),
                                "file_text": "hello world",
                            },
                        }
                    ],
                },
                {"finish_reason": "stop", "text": "Created notes.txt."},
            ],
        }
        tools = [Tool(name=FileEditorTool.name)]
        prompt = f"Create {target} containing the text 'hello world'."
    else:
        scenario = SCENARIO
        tool = WriteFileTool(
            description="Write a text file inside the sandbox directory.",
            action_type=WriteFileAction,
            observation_type=WriteFileObservation,
            executor=WriteFileExecutor(sandbox, trace),
        )
        register_tool("write_file", tool)
        tools = [Tool(name="write_file")]
        prompt = None
    result = run_scenario(
        scenario,
        llm=build_llm(scenario, trace, real=real),
        trace=trace,
        tools=tools,
        workspace=sandbox,
        prompt=prompt,
    )
    result.extra["sandbox"] = sandbox
    result.extra["file_content"] = (
        (sandbox / "notes.txt").read_text() if (sandbox / "notes.txt").exists() else None
    )
    return result


def check(result: RunResult, variant: str | None = None) -> list[str]:
    bad = [] if variant == "file-editor" else check_expect(SCENARIO, result)
    if result.extra.get("file_content") != "hello world":
        bad.append(f"notes.txt content {result.extra.get('file_content')!r}")
    return bad
