# ai-sdk-ts

One [AI SDK Core](https://ai-sdk.dev/docs/reference/ai-sdk-core) (v6) example per scenario in `../scenarios/*.json`
(18 total) in `src/scenarios/<id>.ts`. Each exports `run(model, opts?)` returning a normalised outcome.
See [SUPPORT.md](SUPPORT.md) for the support matrix (no scenario is unsupported; three are partial).

- `src/scenario.ts` – scenario loader, mock tool executor, outcome summariser
- `src/mock.ts` – `scriptedModel()`: `MockLanguageModelV3` that replays a scenario's `mock_llm_script`
- `test/scenarios.test.ts` – keyless tests asserting each scenario's `expect`
- `src/run.ts` – real-LLM runner via OpenRouter (`@ai-sdk/openai-compatible`), local only, never in CI

## Run manually

Keyless checks (all passed locally, Node v22.22.2):

```
npx tsc --noEmit          # no output, exit 0
npx eslint .              # no output, exit 0
npm test                  # tests 25, pass 25, fail 0
```

Real-LLM runner (needs `OPENROUTER_API_KEY`; optional `OPENROUTER_MODEL`, default `openai/gpt-4o-mini`).
I did **not** run it against a real model (no key available in the authoring environment). Without a key it exits:

```
$ npx tsx src/run.ts weather-lookup
OPENROUTER_API_KEY is not set (real runs are local only).
$ echo $?
2
```

Usage: `OPENROUTER_API_KEY=... npx tsx src/run.ts <scenario-id> [variant]` (variants: `approve`/`deny`
for approval scenarios, `required`/`tool` for tool-choice-forced, `has-tool-call` for loop-stop-conditions).
