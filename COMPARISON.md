# Three-way comparison: AI SDK Core (TS) vs OpenHands SDK (Py) vs CrewAI (Py)

Sources: [scenarios/README.md](scenarios/README.md), the three `SUPPORT.md` files and track READMEs, plus the
code in this repo. Versions: `ai@6.0.332` (`^6.0.332` in `package.json`), `openhands-sdk` 1.62.0, `crewai` 1.15.41.
Nothing here was run against a live model (no `OPENROUTER_API_KEY` was available to any track); all behaviour claims
come from keyless scripted-LLM tests and source reading. Items marked **[unverified]** are not backed by a repo test
or SUPPORT file; I only checked that the API name exists in installed source or published docs.

Verdict vocabulary: **supported / partial / emulated / n/a**. AI SDK's SUPPORT.md uses full/partial/unsupported and
OpenHands uses Supported/Partial; both are mapped as full -> supported. No track's own file was reinterpreted.

## Version note: the repo is on AI SDK v6; v7 docs differ

The repo pins `ai` v6 (`MockLanguageModelV3`, `needsApproval`, `stepCountIs`). The current docs (verified at
ai-sdk.dev migration guide 6 -> 7) say:

- `needsApproval` on `tool()` / `dynamicTool()` is deprecated in v7 for `generateText`, `streamText`, `ToolLoopAgent`;
  use the call/agent-level `toolApproval` option instead (`toolApproval: { myTool: 'user-approval' }`, or a function;
  statuses `not-applicable`, `approved`, `denied`, `user-approval`). Old code still works per the docs.
- `stepCountIs` is renamed `isStepCount` (codemod `rename-step-count-is`).
- Also renamed in v7: `system` -> `instructions`, `onFinish` -> `onEnd`, `onStepFinish` -> `onStepEnd`.
- Not migrated here: this repo has not been run on v7, so v7 behaviour is docs-only **[unverified in repo]**.

## Tool definition

- AI SDK: `tool({ description, inputSchema: z.object(...), execute })`, passed as a `tools` map keyed by name.
  Zod `inputSchema` (JSON Schema also possible per docs **[unverified in repo]**).
- OpenHands: a `ToolDefinition` subclass plus pydantic `Action` / `Observation` and a `ToolExecutor`. `name` is a
  ClassVar, so the harness generates one subclass per mock tool. Built-in `FileEditorTool` is also used. The agent
  injects optional `security_risk` / `summary` fields into every tool schema; executors drop them.
- CrewAI: `@tool` function or `BaseTool` subclass with a pydantic `args_schema`, attached via `Agent(tools=[...])`.

## Schema validation

- AI SDK: schema failure produces `InvalidToolInputError` on an `invalid` tool-call part and a `tool-error` fed back to
  the model; `execute` never runs. Unknown names give `NoSuchToolError` the same way.
- OpenHands: the `Action` pydantic model validates; failures become `AgentErrorEvent(validation_errors=...)`. Unknown
  tool: `AgentErrorEvent("Tool 'x' not found. Available: [...]")`.
- CrewAI: `BaseTool.run` validates against `args_schema`; error becomes `ToolUsageErrorEvent` plus error text fed back;
  body not run. Unknown tool returns `"Tool not found"` with `ToolUsageFinishedEvent.failure.reason == unknown_tool`.
- In all three, the model gets the error and can recover (scenarios invalid-args-recovery, unknown-tool-name).

## Execution loop

- AI SDK: `generateText` / `streamText` run the loop. Each step = model call + local tool execution; continues while
  the last step ended with tool calls and no `stopWhen` is satisfied. Parallel calls in one step run concurrently.
  No single "stopped by" value; the harness derives `stoppedBy` from `steps`.
- OpenHands: `Agent` + `Conversation.run()`; loops until a terminal `ConversationExecutionStatus` (`finished`,
  `error`, `stuck`, `waiting_for_confirmation`, ...). Built-in `finish` / `think` tools are disabled in this repo
  (`include_default_tools=[]`) so a plain assistant message ends the run.
- CrewAI: `Agent` executing a `Task`; native tool-call path when the LLM reports function-calling support (otherwise
  ReAct text path). Several calls in one turn run as a batch. `Agent(cache=False)` is set here, since the default tool
  cache would hide repeated calls.

## Loop and stop conditions

- AI SDK (all in SUPPORT.md unless noted):
  - `stopWhen`: `stepCountIs(n)` (v7: `isStepCount`), `hasToolCall(name)`, or custom `StopCondition` over `steps`
    (used for stuck detection).
  - `maxOutputTokens` + `finishReason: 'length'` for truncation.
  - `toolChoice`: `'none'`, `'required'`, `{ type: 'tool', toolName }`; per-step forcing via `prepareStep` (a
    top-level forced choice applies to every step).
  - `activeTools` hides tools from the model request (tool-allowlist).
  - `finishReason` values seen: `stop`, `tool-calls`, `length`.
  - `needsApproval` is covered under Approvals.
  - `max_steps` is inferred from the last `finishReason === 'tool-calls'`.
- OpenHands:
  - `Conversation(max_iteration_per_run=N)`: ends with status `ERROR` and `ConversationErrorEvent(code="MaxIterationsReached")`, no exception.
  - Stuck detection: `StuckDetectionThresholds(action_observation=3)` (default 4) -> status `STUCK`.
  - Confirmation policy + security analyzer: see Approvals.
  - Execution status enum: `IDLE, RUNNING, PAUSED, WAITING_FOR_CONFIRMATION, FINISHED, ERROR, STUCK, DELETING`
    (read from installed source).
  - Condenser: `LLMSummarizingCondenser` exists but is **not used** (no scenario has long contexts).
  - `tool_choice` has no Agent option; injected below Agent via `RealLLM.completion(..., tool_choice=...)` -> LiteLLM.
  - Truncation: the SDK ignores `finish_reason`; a truncated text-only turn ends as `finished`. `LLM(max_output_tokens=...)` caps output; `stopped_by="length"` is harness-derived.
  - Allowlist: `Agent(filter_tools_regex=...)`.
- CrewAI:
  - `Agent(max_iter=N)`: after N tool turns one extra "give your final answer" call is made (N+1 LLM calls); no explicit "stopped by max_iter" signal.
  - `Agent(max_execution_time=60)` is set on every run; no scenario exercises a timeout.
  - `max_rpm`: exists on `Agent` in installed source (rate-limit controller) but is **not used or tested** here **[unverified]**.
  - `Task(human_input=True)` reviews the final answer only; it is not the tool-approval mechanism.
  - Stuck loops: built-in `MAX_REPEATED_TOOL_CALLS = 5` exists only in the planning step executor (fixed, not exercised); the repo emulates with `ToolFailure(reason=REPEATED_CALL)` under `ToolFailurePolicy.RAISE`.
  - No `tool_choice`; truncation via `LLM(max_tokens=N)`, and a truncated reply is treated as the final answer. `finish_reason="length"` is visible only on `LLMCallCompletedEvent`.
  - Allowlist is static per agent (`Agent(tools=...)`), no per-step `activeTools` equivalent.

## Streaming and events

- AI SDK: `streamText().fullStream` parts `tool-call`, `tool-result`, `text-delta`, `finish` (scenario vocabulary is
  taken from these). Native.
- OpenHands: `LLM(stream=True)` + `Conversation(token_callbacks=...)` + event callback. Events are `ActionEvent`,
  `ObservationEvent`, `MessageEvent`, mapped by the harness to the scenario vocabulary. The scripted LLM emits synthetic
  chunks; real-provider token streaming not run.
- CrewAI: `crewai_event_bus`: `ToolUsageStartedEvent` (tool-call), `ToolUsageFinishedEvent` (tool-result),
  `LLMStreamChunkEvent` (text-delta), `LLMCallCompletedEvent` (finish). Handlers run on a thread pool: order by
  `emission_sequence`. In the keyless test the stub emits chunks itself; live streaming unverified.

## Approvals

- AI SDK v6: `needsApproval: true`. Not pause/resume: call 1 returns a `tool-approval-request` part, the caller appends
  a `tool-approval-response` and calls again. Denial yields an `execution-denied` result to the model. (v7: `toolApproval`.)
- OpenHands: `SecurityAnalyzerBase` subclass (`requires_approval` -> HIGH) + `ConfirmRisky(HIGH)`. `run()` pauses in
  `WAITING_FOR_CONFIRMATION`; approve = `run()` again; deny = `reject_pending_actions()` (a `UserRejectObservation` is
  fed back). Closest to a real pause/resume.
- CrewAI: global `PRE_TOOL_CALL` hook (`@on(InterceptionPoint.PRE_TOOL_CALL, tools=[...])`) with
  `ctx.request_human_input`; `raise HookAborted` skips the tool. The model sees only the generic
  `"Tool execution blocked by hook. Tool: <name>"`, not the reason. Hooks are process-global (register/unregister around the run).
  A custom exception raised in a hook is swallowed, so hooks block one call but cannot abort the run.

## Sandboxing

- None of the three provides sandboxing used by this repo. `file-write` writes into a sandbox directory chosen by the
  harness in each track (AI SDK `execute` writes inside a sandbox dir; CrewAI "real write in a sandbox dir"; OpenHands
  hand-written tool plus a `FileEditorTool` variant). Process/container isolation is not exercised in any track;
  OpenHands `TerminalTool` is not used. OpenHands' wider runtime/workspace isolation features are **[unverified]**.

## Error handling

- Tool exceptions are turned into model-visible errors in all three; the run continues:
  - AI SDK: `execute` throw -> `tool-error` part; `generateText` does not throw.
  - OpenHands: executor may return `Observation(is_error=True)` or raise; raised exceptions become an error event (verified with `RuntimeError`).
  - CrewAI: exception caught -> `ToolUsageErrorEvent`, text fed back (default `ToolFailurePolicy.WARN`); `RAISE` aborts with `ToolExecutionFailedError`.
- Run-level limits: AI SDK returns normally (inspect `steps`); OpenHands returns status `ERROR` + `ConversationErrorEvent`; CrewAI returns the forced final answer.

## Provider support

- AI SDK: provider-agnostic via provider packages; the repo uses `@ai-sdk/openai-compatible` (OpenRouter) for
  `src/run.ts` and `MockLanguageModelV3` for tests.
- OpenHands: LiteLLM underneath (`LLM` class; `RealLLM` -> LiteLLM). Repo runner uses OpenRouter.
- CrewAI: `LLM` / `BaseLLM`; repo runner uses OpenRouter. The native OpenAI provider sets `tool_choice="auto"` internally when tools are sent.
- No live-model run exists for any track. Real-LLM runners all refuse without `OPENROUTER_API_KEY`.

## Per-scenario verdicts

Format: AI SDK / OpenHands / CrewAI. Taken only from the SUPPORT.md files.

- weather-lookup: supported / supported / supported
- file-write: supported / supported / supported
- approval-gated-action: partial (two-call request/response) / supported / supported (caveat: process-global hook)
- loop-stop-conditions: supported / supported / supported (caveat: no explicit stop signal)
- parallel-tool-calls: supported / supported / supported
- sequential-dependent-calls: supported / supported / supported
- tool-choice-forced: supported (via `prepareStep`) / partial (injected below Agent) / n/a
- tool-choice-none: supported / partial (injected below Agent) / emulated (tool hidden, not forbidden)
- invalid-args-recovery: supported / supported / supported
- unknown-tool-name: supported / supported / supported
- tool-throws-error: supported / supported / supported
- max-steps-exceeded: supported / supported / supported (caveat: N+1 calls, inferred)
- max-output-tokens-truncation: supported / partial (SDK ignores `finish_reason`) / partial
- tool-allowlist: supported / supported / supported (static per agent)
- structured-output-after-tools: supported / partial (parsed + validated by harness) / supported
- human-approval-rejected: partial (two-call flow) / supported / supported (caveat: generic block message)
- stuck-loop-detection: partial (custom `StopCondition`) / supported / partial / emulated
- streaming-tool-events: supported / partial (event mapping) / supported (caveat: thread-pool ordering)

Tallies (derived from the list above, counting CrewAI stuck "partial / emulated" as partial): AI SDK 15 supported, 3 partial.
OpenHands 13 supported, 5 partial. CrewAI 14 supported, 2 partial, 1 emulated, 1 n/a.
