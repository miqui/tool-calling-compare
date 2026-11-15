# OpenHands SDK support notes

Verified against `openhands-sdk` 1.62.0 (+ `openhands-tools`) by reading the installed source
and by running every scenario through the real `Agent` / `Conversation` with a scripted LLM.

All 18 scenarios have an example in `src/tcc_openhands/scenarios/<id>.py`. Fully supported
unless listed below.

| Scenario | Status | Reason / how it is done |
|---|---|---|
| tool-choice-forced, tool-choice-none | Partial | `Agent` has no `tool_choice` option. It is injected one layer down: `RealLLM.completion(..., tool_choice=...)` -> LiteLLM (a test patches `litellm_completion` and asserts the kwarg is sent). Not an Agent feature. |
| max-output-tokens-truncation | Partial | The SDK never looks at `finish_reason`: a truncated text-only turn ends the run as `finished`. We cap output with `LLM(max_output_tokens=...)` and read `finish_reason` from the LLM response ourselves (`stopped_by="length"` is harness-derived). Truncated *tool-call* JSON would surface as an argument-validation `AgentErrorEvent`, but is not scripted by this scenario. |
| structured-output-after-tools | Partial | No native schema-constrained final answer for `Agent` runs. The final assistant message is parsed as JSON and checked against `output_schema` by a small validator in `checks.py`; the schema is also put in the prompt for real-LLM runs. |
| streaming-tool-events | Partial | Supported via `LLM(stream=True)` + `Conversation(token_callbacks=...)` + event callback. SDK events are `ActionEvent` / `ObservationEvent` / `MessageEvent`, mapped to the scenario vocabulary (`tool-call`, `tool-result`, `text-delta`, `finish`). The scripted LLM emits synthetic chunks; token streaming against a real provider was not run (no key). |
| human-approval-rejected, approval-gated-action | Supported | `SecurityAnalyzerBase` subclass (`requires_approval` -> HIGH) + `ConfirmRisky(HIGH)`; `run()` pauses in `WAITING_FOR_CONFIRMATION`; approve = `run()` again, deny = `reject_pending_actions()` (a `UserRejectObservation` is fed back). |
| stuck-loop-detection | Supported | `Conversation(stuck_detection_thresholds=StuckDetectionThresholds(action_observation=3))`; status `STUCK`. Default threshold is 4. |
| max-steps-exceeded, loop-stop-conditions | Supported | `Conversation(max_iteration_per_run=N)`; the run ends with status `ERROR` + `ConversationErrorEvent(code="MaxIterationsReached")` (no exception). |
| tool-allowlist | Supported | `Agent(filter_tools_regex=...)`; the LLM only receives the allowed tool schemas. |
| invalid-args-recovery | Supported | The `Action` pydantic model validates; failures become `AgentErrorEvent(validation_errors=...)`. |
| unknown-tool-name | Supported | `AgentErrorEvent("Tool 'x' not found. Available: [...]")`. |
| tool-throws-error | Supported | Executors may return `Observation(is_error=True)` or raise; raised exceptions are converted to an error event and the loop continues (verified with `RuntimeError`). |
| file-write | Supported | Hand-written Action/Observation/ToolExecutor tool, plus a variant using the built-in `FileEditorTool` (`file_editor create`). |

## Not used

- **Condenser** (`LLMSummarizingCondenser`): no scenario involves long contexts, so none is wired in.
- **TerminalTool**: no scenario needs a shell; `FileEditorTool` is exercised in `file-write`.

## Notes / quirks

- Built-in `finish` and `think` tools are disabled (`include_default_tools=[]`) so the tool set
  equals the scenario's and a plain assistant message ends the run.
- `ToolDefinition.name` is a ClassVar, so each mock tool gets its own generated subclass.
- Agent injects optional `security_risk` / `summary` fields into tool schemas; executors drop them
  before recording calls.
- Scenario files have hyphens, so modules are loaded via `tcc_openhands.scenarios.load(id)`.
- Real-LLM runs (`python -m tcc_openhands.run <id>`) need `OPENROUTER_API_KEY` and were **not**
  executed when this was written (no key available); only the keyless/scripted paths are verified.
