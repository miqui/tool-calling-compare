# CrewAI support matrix

Verified against `crewai 1.15.41` (pinned in `uv.lock`), by reading its installed source and by the
keyless tests in `tests/test_scenarios.py` (stub LLM = `BaseLLM` subclass replaying each
scenario's `mock_llm_script`). Nothing here was verified against a live model: no
`OPENROUTER_API_KEY` was available when this track was written.

Legend: **supported** = native CrewAI mechanism, **partial** = works with a stated gap,
**emulated** = reproduced with a workaround, **n/a** = no CrewAI mechanism.

| Scenario | Verdict | How / reason |
|---|---|---|
| weather-lookup | supported | `@tool` function; native tool-call path |
| file-write | supported | `BaseTool` + pydantic `args_schema`, real write in a sandbox dir |
| sequential-dependent-calls | supported | two `@tool`s; one LLM turn per call |
| parallel-tool-calls | supported | several calls in one turn are executed as a batch by the native executor |
| invalid-args-recovery | supported | `BaseTool.run` validates against `args_schema`; error becomes a `ToolUsageErrorEvent` and text fed back; the body never runs on invalid args |
| unknown-tool-name | supported | result `"Tool not found"`, `ToolUsageFinishedEvent.failure.reason == unknown_tool`; model recovers |
| tool-throws-error | supported | exception caught, `ToolUsageErrorEvent`, error text fed back (default `ToolFailurePolicy.WARN`) |
| max-steps-exceeded | supported (caveat) | `Agent(max_iter=N)`. After N tool turns CrewAI makes one extra "give your final answer" LLM call (N+1 calls) and returns that text; there is no explicit "stopped by max_iter" signal, it is inferred from the call count |
| loop-stop-conditions | supported (caveat) | same as max-steps-exceeded |
| max-output-tokens-truncation | partial | `LLM(max_tokens=N)` sets the limit. A truncated reply is treated as the final answer (a cut-off tool-call JSON is never parsed or executed). `finish_reason="length"` is visible only on `LLMCallCompletedEvent`; the executor does not act on it |
| tool-allowlist | supported | expose a subset by passing only it to `Agent(tools=...)`; static per agent (no per-step `activeTools`) |
| structured-output-after-tools | supported | `Task(output_pydantic=Model)`; result on `CrewOutput.pydantic` |
| human-approval-rejected | supported (caveat) | global `PRE_TOOL_CALL` hook (`@on(InterceptionPoint.PRE_TOOL_CALL, tools=[...])`) with `ctx.request_human_input`; `raise HookAborted` skips the tool. The model only sees the generic `"Tool execution blocked by hook. Tool: <name>"`, not the reason. `Task(human_input=True)` is *not* this: it reviews the final answer only |
| approval-gated-action | supported (caveat) | same hook; approve and deny variants tested. Hooks are process-global, so register/unregister around the run (`approval_gate`) |
| stuck-loop-detection | partial / emulated | the built-in repeated-call stop (`MAX_REPEATED_TOOL_CALLS = 5`, reason `REPEATED_CALL`) exists only in the planning step executor, with a fixed limit, and was not exercised. Emulated: the tool returns `ToolFailure(reason=REPEATED_CALL)` at the threshold under `ToolFailurePolicy.RAISE`, aborting with `ToolExecutionFailedError`. A custom exception raised in a hook is swallowed (verified), so hooks cannot abort the run, only block one call |
| streaming-tool-events | supported (caveat) | event bus: `ToolUsageStartedEvent` (tool-call), `ToolUsageFinishedEvent` (tool-result), `LLMStreamChunkEvent` (text-delta), `LLMCallCompletedEvent` (finish). Handlers run on a thread pool, so order by `emission_sequence`, not arrival. In the keyless test the stub emits the chunk events itself; real providers emit them with `LLM(stream=True)` (unverified live) |
| tool-choice-none | emulated | no `tool_choice` option. The tool is simply not passed to the agent (no tools => no schemas sent). This hides the tool rather than forbidding calls |
| tool-choice-forced | n/a | no `tool_choice` on `Agent`, `Task`, `BaseLLM` or `LLM` (asserted in a test), and the native OpenAI provider sets `tool_choice="auto"` internally whenever tools are sent. Narrowing the tool list to the forced tool is implemented but cannot force the model to call it, so neither `required` nor a specific tool is honoured |

## Other notes

- `Agent(cache=False)` is set in the harness. With the default cache, identical repeated calls are
  served from the tool cache and the body does not run again, which would hide stuck loops.
- The native tool-call path is used because the stub reports `supports_function_calling() == True`;
  without tools, CrewAI falls back to its text (ReAct) path.
- `Agent(max_execution_time=60)` is set on every run; no scenario exercises a timeout.
