"""Keyless tests: every scenario driven through the real OpenHands Agent/Conversation by a
scripted LLM (``openhands.sdk.testing.TestLLM`` subclass) following ``mock_llm_script``."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
os.environ.setdefault("LOG_LEVEL", "ERROR")

from tcc_openhands.checks import event_order  # noqa: E402
from tcc_openhands.harness import SCENARIOS_DIR, load_scenario  # noqa: E402
from tcc_openhands.scenarios import IDS, load  # noqa: E402

VARIANTS = {
    "approval-gated-action": ["approve", "deny"],
    "tool-choice-forced": ["required", "tool"],
    "tool-throws-error": ["observation", "raises"],
    "file-write": ["custom", "file-editor"],
}


class AllScenariosTest(unittest.TestCase):
    def test_every_scenario_has_an_example(self) -> None:
        on_disk = sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
        self.assertEqual(IDS, on_disk)

    def test_each_scenario_matches_expect(self) -> None:
        for sid in IDS:
            for variant in VARIANTS.get(sid, [None]):
                with self.subTest(scenario=sid, variant=variant):
                    mod = load(sid)
                    result = mod.run(variant=variant)
                    self.assertEqual(mod.check(result, variant), [], result.final_text)


class SpecificBehaviourTest(unittest.TestCase):
    def test_sdk_terminal_statuses(self) -> None:
        self.assertEqual(load("weather-lookup").run().status, "finished")
        self.assertEqual(load("max-steps-exceeded").run().status, "error")
        self.assertEqual(load("stuck-loop-detection").run().status, "stuck")

    def test_parallel_calls_share_one_llm_step(self) -> None:
        r = load("parallel-tool-calls").run()
        self.assertEqual(r.steps, 2)
        self.assertEqual(len(r.executed_calls), 2)

    def test_invalid_args_never_reach_executor(self) -> None:
        r = load("invalid-args-recovery").run()
        self.assertEqual(r.validation_errors, 1)
        self.assertEqual(r.executed_calls, [{"name": "set_timer", "arguments": {"minutes": 5}}])

    def test_unknown_tool_not_executed(self) -> None:
        r = load("unknown-tool-name").run()
        self.assertEqual(r.unknown_tool_errors, 1)
        self.assertEqual([c["name"] for c in r.executed_calls], ["get_weather"])

    def test_denied_approval_does_not_execute(self) -> None:
        r = load("human-approval-rejected").run()
        self.assertTrue(r.paused_for_confirmation)
        self.assertEqual(r.executed_calls, [])
        self.assertEqual(r.rejected, 1)

    def test_allowlist_hides_unlisted_tool(self) -> None:
        r = load("tool-allowlist").run()
        self.assertEqual(r.trace.exposed_tools, ["read_file"])

    def test_truncation_is_observed_not_acted_on(self) -> None:
        r = load("max-output-tokens-truncation").run()
        self.assertEqual(r.trace.finish_reasons, ["length"])
        self.assertEqual(r.status, "finished")  # SDK itself ends normally
        self.assertEqual(r.stopped_by, "length")

    def test_streaming_event_order(self) -> None:
        r = load("streaming-tool-events").run()
        self.assertEqual(event_order(r), ["tool-call", "tool-result", "text-delta", "finish"])

    def test_scenario_json_unchanged_shape(self) -> None:
        self.assertEqual(load_scenario("weather-lookup")["id"], "weather-lookup")


class RealLLMWiringTest(unittest.TestCase):
    def test_tool_choice_reaches_litellm(self) -> None:
        """RealLLM with the litellm call patched: tool_choice must be in the request kwargs."""
        from unittest.mock import patch

        from litellm.types.utils import Choices, ModelResponse
        from litellm.types.utils import Message as LMsg
        from openhands.sdk import Message, TextContent
        from pydantic import SecretStr

        from tcc_openhands.harness import RealLLM, Trace, make_tool

        resp = ModelResponse(
            id="x",
            choices=[Choices(message=LMsg(role="assistant", content="hi"), finish_reason="stop")],
            model="m",
        )
        llm = RealLLM(model="openrouter/test/model", api_key=SecretStr("k"), usage_id="t")
        llm.trace = Trace()
        llm.tool_choice = "required"
        tool = make_tool(load_scenario("weather-lookup")["tools"][0], Trace())
        with patch("openhands.sdk.llm.llm.litellm_completion", return_value=resp) as m:
            llm.completion([Message(role="user", content=[TextContent(text="hi")])], tools=[tool])
        self.assertEqual(m.call_args.kwargs.get("tool_choice"), "required")
        self.assertEqual(llm.trace.llm_calls, 1)


if __name__ == "__main__":
    unittest.main()
