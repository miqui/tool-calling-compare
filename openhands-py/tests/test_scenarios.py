import json
import unittest
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "scenarios"
LEGACY = {"weather-lookup", "file-write", "approval-gated-action", "loop-stop-conditions"}
STOPS = {"final_answer", "max_steps", "truncated", "stuck_detected", "structured_output"}
FINISH = {"stop", "tool_calls", "length"}
TOOL_KEYS = {
    "name",
    "description",
    "parameters",
    "mock_result",
    "mock_result_by_args",
    "mock_result_sequence",
    "mock_error",
    "requires_approval",
}


def check(s: dict, stem: str) -> list[str]:
    e: list[str] = []
    for k in ("id", "description", "prompt"):
        if not isinstance(s.get(k), str) or not s[k]:
            e.append(f"missing string {k}")
    if s.get("id") != stem:
        e.append("id != filename")
    tools = s.get("tools")
    if not isinstance(tools, list) or not tools:
        return [*e, "tools must be non-empty list"]
    names = set()
    for t in tools:
        names.add(t.get("name"))
        if not isinstance(t.get("name"), str):
            e.append("tool without name")
        params = t.get("parameters")
        if not isinstance(params, dict):
            e.append(f"tool {t.get('name')}: parameters must be object")
        elif params.get("type") == "object" and not isinstance(params.get("properties"), dict):
            e.append(f"tool {t.get('name')}: JSON schema needs properties")
        if set(t) - TOOL_KEYS:
            e.append(f"tool {t.get('name')}: unknown keys {set(t) - TOOL_KEYS}")
    if stem in LEGACY:
        return e
    if not isinstance(s.get("title"), str):
        e.append("missing title")
    if not s.get("features"):
        e.append("missing features")
    if s.get("stop_condition") not in STOPS:
        e.append("bad stop_condition")
    if not isinstance(s.get("expect"), dict):
        e.append("missing expect")
    for t in tools:
        if not t.get("description"):
            e.append(f"tool {t.get('name')}: missing description")
        if not any(k in t for k in ("mock_result", "mock_result_by_args", "mock_error")):
            e.append(f"tool {t.get('name')}: no deterministic mock")
    script = s.get("mock_llm_script")
    if not script:
        e.append("missing mock_llm_script")
    for turn in script or []:
        if turn.get("finish_reason") not in FINISH:
            e.append("bad finish_reason")
        for c in turn.get("tool_calls", []):
            if "name" not in c or not isinstance(c.get("arguments"), dict):
                e.append("bad scripted tool call")
    for a in s.get("active_tools") or []:
        if a not in names:
            e.append(f"active_tools unknown {a}")
    return e


class ScenarioSchemaTest(unittest.TestCase):
    def test_all_scenarios_valid(self) -> None:
        files = sorted(DIR.glob("*.json"))
        self.assertGreaterEqual(len(files), 12)
        ids = [f.stem for f in files]
        self.assertTrue(LEGACY <= set(ids))
        for f in files:
            with self.subTest(scenario=f.stem):
                self.assertEqual(check(json.loads(f.read_text()), f.stem), [])


if __name__ == "__main__":
    unittest.main()
