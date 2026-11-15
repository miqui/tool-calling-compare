# Scenario schema

One JSON file per scenario, `scenarios/<id>.json`; `id` must equal the filename.
Validated keylessly by `openhands-py/tests/test_scenarios.py` (runs in CI job `lint-py`).

## Fields

| Field | Req. | Notes |
|---|---|---|
| `id`, `description`, `prompt` | yes | strings |
| `tools[]` | yes | `name`, `parameters`; optional `description`, `mock_result`, `mock_result_by_args`, `mock_result_sequence`, `mock_error`, `requires_approval` |
| `tools[].parameters` | yes | legacy: map of name -> type string; new: JSON Schema object (`"type": "object"`) |
| `title`, `features[]`, `stop_condition`, `expect`, `mock_llm_script[]` | yes for new scenarios | legacy four (weather-lookup, file-write, approval-gated-action, loop-stop-conditions) are exempt |
| `stop_condition` | | `final_answer`, `max_steps`, `truncated`, `stuck_detected`, `structured_output` |
| `mock_llm_script[]` | | scripted assistant turns: `finish_reason` (`stop`/`tool_calls`/`length`), optional `text`, `tool_calls[{name,arguments}]`. Lets a mock LLM drive the scenario keylessly. Tool results come from the tool mocks. |
| `expect` | | expected tool-call sequence (`tool_calls`), plus assertions such as `steps`, `stopped_by`, `executed_tool_calls`, `final_answer_contains` |
| optional config | | `tool_choice` (`none`/`required`/`{tool}`), `active_tools`, `output_schema`, `limits`, `approval`, `streaming`, `variants` |

All extensions are additive; legacy files are unchanged.

## Scenarios

weather-lookup, file-write, approval-gated-action, loop-stop-conditions (legacy);
parallel-tool-calls, sequential-dependent-calls, tool-choice-forced, tool-choice-none,
invalid-args-recovery, unknown-tool-name, tool-throws-error, max-steps-exceeded,
max-output-tokens-truncation, tool-allowlist, structured-output-after-tools,
human-approval-rejected, stuck-loop-detection, streaming-tool-events.
