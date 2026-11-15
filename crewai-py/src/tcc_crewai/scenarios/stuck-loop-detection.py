"""stuck-loop-detection: emulated with ToolFailure(REPEATED_CALL) + ToolFailurePolicy.RAISE.

CrewAI's built-in repeated-call stop lives only in the planning step executor with a fixed limit
of 5 (MAX_REPEATED_TOOL_CALLS), so the standard loop has no detector with a configurable
threshold. A tool may return `ToolFailure`; under the RAISE policy the run aborts with
`ToolExecutionFailedError`. (Raising a custom exception from a hook is swallowed by CrewAI.)
"""

import json
from typing import Any

from crewai.tools.tool_failure import ToolFailure, ToolFailurePolicy, ToolFailureReason
from pydantic import BaseModel, PrivateAttr

from tcc_crewai.common import MockBackedTool, MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "stuck-loop-detection"


class ClickArgs(BaseModel):
    target: str


class Click(MockBackedTool):
    name: str = "click"
    description: str = "Click a UI element."
    args_schema: type[BaseModel] = ClickArgs
    tool_failure_policy: ToolFailurePolicy | None = ToolFailurePolicy.RAISE
    _threshold: int = PrivateAttr(default=3)
    _last: str | None = PrivateAttr(default=None)
    _streak: int = PrivateAttr(default=0)

    def __init__(self, mock: MockTool, threshold: int, **data: Any) -> None:
        super().__init__(mock=mock, **data)
        self._threshold = threshold

    def _run(self, **kwargs: Any) -> Any:
        result = self._mock(**kwargs)
        key = json.dumps(kwargs, sort_keys=True)
        self._streak = self._streak + 1 if key == self._last else 1
        self._last = key
        if self._streak >= self._threshold:
            return ToolFailure(
                message=f"click called {self._streak}x with identical arguments: stuck",
                reason=ToolFailureReason.REPEATED_CALL,
            )
        return result


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    mock = MockTool(tool_spec(sc, "click"))
    limits = sc["limits"]
    tool = Click(mock=mock, threshold=limits["repeat_threshold"])
    return execute(sc, [tool], {"click": mock}, llm, max_iter=limits["max_steps"])
