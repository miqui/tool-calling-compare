"""Keyless tests: every scenario driven by the scripted stub LLM (no network, no API keys)."""

import json
import tempfile
import unittest
from pathlib import Path

from crewai import LLM, Agent, Task
from crewai.llms.base_llm import BaseLLM
from crewai.tools.tool_failure import ToolExecutionFailedError

from tcc_crewai import scenarios
from tcc_crewai.common import SCENARIOS_DIR, ScriptedLLM, load_scenario


def mod(scenario_id: str):
    return scenarios.load(scenario_id)


class CoverageTests(unittest.TestCase):
    def test_every_scenario_json_has_a_module(self) -> None:
        ids = sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
        self.assertEqual(len(ids), 18)
        self.assertEqual(ids, scenarios.SCENARIO_IDS)
        for scenario_id in ids:
            self.assertEqual(
                json.loads((SCENARIOS_DIR / f"{scenario_id}.json").read_text())["id"], scenario_id
            )
            self.assertEqual(mod(scenario_id).SCENARIO_ID, scenario_id)

    def test_stub_is_a_public_base_llm(self) -> None:
        self.assertTrue(issubclass(ScriptedLLM, BaseLLM))


class BasicToolTests(unittest.TestCase):
    def test_weather_lookup(self) -> None:
        run = mod("weather-lookup").run()
        self.assertEqual(run.obs.attempted(), [("get_weather", {"city": "Paris"})])
        self.assertIn("18", run.obs.raw)
        self.assertEqual(run.executed("get_weather"), [{"city": "Paris"}])

    def test_file_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = mod("file-write").run(sandbox=Path(tmp))
            self.assertEqual((Path(tmp) / "notes.txt").read_text(), "hello world")
        self.assertEqual(
            run.executed("write_file"), [{"path": "notes.txt", "content": "hello world"}]
        )

    def test_parallel_tool_calls(self) -> None:
        run = mod("parallel-tool-calls").run()
        self.assertEqual(sorted(a["city"] for _, a in run.obs.attempted()), ["Paris", "Tokyo"])
        self.assertEqual(len(run.executed("get_weather")), 2)
        self.assertEqual(len(run.llm.calls), 2)  # one tool turn + final answer
        self.assertTrue(all(x in run.obs.raw for x in ("18", "24")))

    def test_sequential_dependent_calls(self) -> None:
        run = mod("sequential-dependent-calls").run()
        self.assertEqual(
            run.obs.attempted(),
            [
                ("find_user", {"email": "ada@example.com"}),
                ("get_latest_order", {"user_id": "u_42"}),
            ],
        )
        self.assertEqual(len(run.llm.calls), 3)
        self.assertIn("o_900", run.obs.raw)


class ErrorHandlingTests(unittest.TestCase):
    def test_invalid_args_recovery(self) -> None:
        run = mod("invalid-args-recovery").run()
        self.assertEqual(
            run.obs.attempted(),
            [("set_timer", {"minutes": "five"}), ("set_timer", {"minutes": 5})],
        )
        self.assertEqual(run.executed("set_timer"), [{"minutes": 5}])  # invalid call never ran
        self.assertEqual(len(run.obs.tool_errors()), 1)  # ToolUsageErrorEvent (validation)
        self.assertEqual(len(run.llm.calls), 3)

    def test_unknown_tool_name(self) -> None:
        run = mod("unknown-tool-name").run()
        self.assertEqual([n for n, _ in run.obs.attempted()], ["get_forecast", "get_weather"])
        self.assertEqual(run.executed("get_weather"), [{"city": "Paris"}])
        first = run.obs.results()[0]
        self.assertEqual(first.output, "Tool not found")
        self.assertEqual(first.failure.reason.value, "unknown_tool")
        self.assertEqual(len(run.llm.calls), 3)

    def test_tool_throws_error(self) -> None:
        run = mod("tool-throws-error").run()
        self.assertEqual(
            run.obs.attempted(), [("fetch_url", {"url": "https://status.example.com"})]
        )
        errors = run.obs.tool_errors()
        self.assertEqual(len(errors), 1)
        self.assertIn("connection refused", str(errors[0].error))
        self.assertEqual(len(run.llm.calls), 2)
        self.assertIn("refused", run.obs.raw)
        self.assertIsNone(run.obs.error)


class LimitTests(unittest.TestCase):
    def test_max_steps_exceeded(self) -> None:
        run = mod("max-steps-exceeded").run()
        self.assertEqual(len(run.obs.attempted()), 3)
        self.assertEqual(len(run.executed("check_queue")), 3)
        # CrewAI makes one extra "forced final answer" call after max_iter tool turns.
        self.assertEqual(run.llm.overflow_calls, 1)
        self.assertEqual(len(run.llm.calls), 4)
        self.assertEqual(run.obs.raw, run.llm.fallback_text)

    def test_loop_stop_conditions(self) -> None:
        run = mod("loop-stop-conditions").run()
        self.assertEqual(len(run.executed("poll_status")), 3)
        self.assertEqual(run.llm.overflow_calls, 1)

    def test_max_output_tokens_truncation(self) -> None:
        run = mod("max-output-tokens-truncation").run()
        self.assertEqual(run.llm.max_tokens, 16)  # configured limit
        self.assertEqual(run.executed("write_file"), [])  # partial tool call never executed
        self.assertEqual(run.obs.attempted(), [])
        # The only signal is the completion event; CrewAI treats the truncated text as the answer.
        self.assertEqual(run.obs.finish_reasons(), ["length"])
        self.assertTrue(run.obs.raw.startswith('{"path":"report.txt"'))

    def test_stuck_loop_detection(self) -> None:
        run = mod("stuck-loop-detection").run()
        self.assertIsInstance(run.obs.error, ToolExecutionFailedError)
        self.assertEqual(run.obs.error.record.failure.reason.value, "repeated_call")
        self.assertEqual(len(run.executed("click")), 3)  # == repeat_threshold
        self.assertEqual(len(run.llm.calls), 3)
        self.assertEqual(run.llm.overflow_calls, 0)  # stopped, no forced final answer


class ExposureTests(unittest.TestCase):
    def test_tool_allowlist(self) -> None:
        run = mod("tool-allowlist").run()
        self.assertEqual(run.llm.calls[0]["tools"], ["read_file"])
        self.assertEqual(run.executed("delete_file"), [])
        self.assertEqual(run.executed("read_file"), [{"path": "old.txt"}])
        self.assertEqual(len(run.llm.calls), 2)

    def test_tool_choice_none_is_emulated_by_hiding_tools(self) -> None:
        run = mod("tool-choice-none").run()
        self.assertEqual(run.llm.calls[0]["tools"], [])
        self.assertEqual(run.obs.attempted(), [])
        self.assertEqual(run.executed("get_weather"), [])
        self.assertEqual(len(run.llm.calls), 1)

    def test_tool_choice_forced_has_no_native_option(self) -> None:
        for model in (Agent, Task, BaseLLM, LLM):
            self.assertNotIn("tool_choice", model.model_fields, model.__name__)
        for variant in (0, 1):
            run = mod("tool-choice-forced").run(variant=variant)
            self.assertEqual(run.llm.calls[0]["tools"], ["log_greeting"])  # narrowing only
            self.assertEqual(run.obs.attempted(), [("log_greeting", {"text": "hello"})])
            self.assertEqual(len(run.llm.calls), 2)
        self.assertEqual(
            load_scenario("tool-choice-forced")["variants"][0]["tool_choice"], "required"
        )


class ApprovalTests(unittest.TestCase):
    def test_human_approval_rejected(self) -> None:
        run = mod("human-approval-rejected").run()
        self.assertEqual(run.executed("transfer_funds"), [])
        self.assertEqual(
            run.obs.attempted(), [("transfer_funds", {"account": "123", "amount": 500})]
        )
        self.assertEqual(
            run.obs.results()[0].output, "Tool execution blocked by hook. Tool: transfer_funds"
        )
        self.assertEqual(
            run.extras["decisions"], [("transfer_funds", {"account": "123", "amount": 500}, False)]
        )
        self.assertIn("denied", run.obs.raw)

    def test_approval_gated_action_approve_and_deny(self) -> None:
        approved = mod("approval-gated-action").run(variant="approve")
        self.assertEqual(approved.executed("delete_file"), [{"path": "old-report.txt"}])
        denied = mod("approval-gated-action").run(variant="deny")
        self.assertEqual(denied.executed("delete_file"), [])
        self.assertIn("denied", denied.obs.raw)

    def test_hook_is_unregistered_after_run(self) -> None:
        from crewai.hooks import InterceptionPoint, get_hooks

        mod("human-approval-rejected").run()
        self.assertEqual(get_hooks(InterceptionPoint.PRE_TOOL_CALL), [])


class OutputTests(unittest.TestCase):
    def test_structured_output_after_tools(self) -> None:
        run = mod("structured-output-after-tools").run()
        result = run.obs.output.pydantic
        self.assertEqual((result.city, result.temp_c), ("Paris", 18))
        self.assertEqual(run.obs.attempted(), [("get_weather", {"city": "Paris"})])
        self.assertEqual(len(run.llm.calls), 2)

    def test_streaming_tool_events(self) -> None:
        run = mod("streaming-tool-events").run()
        self.assertEqual(
            run.obs.event_order(), ["tool-call", "tool-result", "text-delta", "finish"]
        )
        deltas = [e.chunk for k, e in run.obs.events if k == "text-delta"]
        self.assertEqual("".join(deltas).strip(), "18C and cloudy.")


if __name__ == "__main__":
    unittest.main()
