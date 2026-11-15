# tool-calling-compare

Side-by-side comparison of tool calling in two agent stacks:

- **TypeScript** – [Vercel AI SDK Core](https://ai-sdk.dev) (`ai-sdk-ts/`)
- **Python** – [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk) (`openhands-py/`)

Both implement the same language-neutral scenarios so behaviour can be compared directly.

> Status: scaffold only. Source files are placeholders with keyless mock tests.

## Layout

```
scenarios/        JSON specs: weather-lookup, file-write,
                  approval-gated-action, loop-stop-conditions
ai-sdk-ts/        Node 22 (.nvmrc), TypeScript strict, eslint, node:test
openhands-py/     uv project, Python 3.12 (.python-version), ruff, unittest
.github/workflows/ci.yml   jobs: lint-ts, lint-py (keyless)
```

## CI

CI never uses LLM keys. `lint-ts`: `npm ci`, `tsc --noEmit`, `eslint .`, mock tests.
`lint-py`: `uv sync`, `ruff check`, `ruff format --check`, `unittest`.
Real LLM runs are local only, via the `OPENROUTER_API_KEY` environment variable (not yet implemented).

## Run manually

TypeScript (from `ai-sdk-ts/`), all passed locally:

```
npm install
npx tsc --noEmit          # no output, exit 0
npx eslint .              # no output, exit 0
npm test                  # tests 1, pass 1, fail 0
```

Python (from `openhands-py/`), all passed locally:

```
uv sync
uv run ruff check .                                   # All checks passed!
uv run ruff format --check .                          # 2 files already formatted
uv run python -m unittest discover -s tests           # Ran 1 test ... OK
```
