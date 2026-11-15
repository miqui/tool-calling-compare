# AI SDK Core support matrix

Implemented against `ai@6.0.x` (`npm ls ai` shows the exact version) using `generateText` / `streamText`,
`tool()` with zod `inputSchema`, and the keyless `MockLanguageModelV3` from `ai/test`.

Status: **full** = expressed with built-in APIs; **partial** = works but needs custom code or differs in semantics;
**unsupported** = cannot be expressed (none).

| Scenario | Status | AI SDK APIs / notes |
|---|---|---|
| weather-lookup | full | `generateText`, `stopWhen: stepCountIs(5)` |
| file-write | full | `execute` writes inside a sandbox dir |
| approval-gated-action | partial | `needsApproval: true`; not a pause/resume: call 1 returns a `tool-approval-request`, caller appends a `tool-approval-response` and calls again |
| loop-stop-conditions | full | `stepCountIs`, `hasToolCall` variant |
| parallel-tool-calls | full | two calls in one step, executed concurrently by default |
| sequential-dependent-calls | full | multi-step loop |
| tool-choice-forced | full | `toolChoice` `'required'` / `{ type: 'tool', toolName }` set via `prepareStep` for step 0 only (a top-level forced choice applies to every step) |
| tool-choice-none | full | `toolChoice: 'none'` |
| invalid-args-recovery | full | schema failure -> `InvalidToolInputError` on the `invalid` tool-call part, `tool-error` fed back; `execute` never runs |
| unknown-tool-name | full | `NoSuchToolError`, same mechanism |
| tool-throws-error | full | `execute` exception becomes a `tool-error` part; `generateText` does not throw |
| max-steps-exceeded | full | `stepCountIs(3)`; "max_steps" inferred from last `finishReason === 'tool-calls'` |
| max-output-tokens-truncation | full | `maxOutputTokens`, `finishReason: 'length'` |
| tool-allowlist | full | `activeTools: ['read_file']` (hidden from the model request) |
| structured-output-after-tools | full | `output: Output.object({ schema })` + tools, `result.output` |
| human-approval-rejected | partial | as approval-gated-action, with a denied response (`execution-denied` result goes to the model) |
| stuck-loop-detection | partial | no built-in repeat detector; custom `StopCondition` over `steps` (`repeatedToolCalls`) |
| streaming-tool-events | full | `streamText().fullStream` part types `tool-call`, `tool-result`, `text-delta`, `finish` |

## Notes

- `needsApproval` exists in v6; newer majors deprecate it in favour of a `toolApproval` option.
- Outcome fields (`stoppedBy`, error counts) are derived from `steps` by `src/scenario.ts`; the SDK has no single "stopped by" value.
- Legacy scenarios (weather-lookup, file-write, approval-gated-action, loop-stop-conditions) have no `mock_llm_script`
  in their JSON, so their scripts live in the scenario modules (`script`).
