# tool-calling-compare

Side-by-side comparison of tool calling in three agent stacks, all driven by the same language-neutral scenarios:

- **TypeScript** – [Vercel AI SDK Core](https://ai-sdk.dev) v6 (`ai-sdk-ts/`) – [SUPPORT.md](ai-sdk-ts/SUPPORT.md)
- **Python** – [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk) (`openhands-py/`) – [SUPPORT.md](openhands-py/SUPPORT.md)
- **Python** – [CrewAI](https://github.com/crewAIInc/crewAI) (`crewai-py/`) – [SUPPORT.md](crewai-py/SUPPORT.md)

The three-way write-up is in **[COMPARISON.md](COMPARISON.md)** (per-scenario verdicts are copied from the SUPPORT files).

> Status: all 18 scenarios have an example in every track, verified only with keyless scripted/mock LLMs.
> No track has been run against a live model.

## Layout

```
scenarios/        18 JSON specs + README.md (schema, scenario list)
ai-sdk-ts/        Node 22 (.nvmrc), TypeScript strict, eslint, node:test
openhands-py/     uv project, Python 3.12, ruff, unittest
crewai-py/        uv project, Python 3.12 (.python-version), ruff, unittest
COMPARISON.md     three-way comparison
.github/workflows/ci.yml   jobs: lint-ts, lint-py (openhands-py and crewai-py steps), keyless
```

## CI

CI never uses LLM keys. `lint-ts`: `npm ci`, `tsc --noEmit`, `eslint .`, mock tests.
`lint-py`: for both `openhands-py` and `crewai-py`: `uv sync`, `ruff check`, `ruff format --check`, `unittest`.
Real LLM runs are local only, via the `OPENROUTER_API_KEY` environment variable; none has been executed yet.

## Run manually

Results below were produced locally on this checkout (Node v22.22.2, `ai@6.0.332`).

TypeScript (from `ai-sdk-ts/`):

```
npm ci
npx tsc --noEmit          # no output, exit 0
npx eslint .              # no output, exit 0
npm test                  # tests 25, pass 25, fail 0
```

OpenHands (from `openhands-py/`):

```
uv sync
uv run ruff check .                                   # All checks passed!
uv run ruff format --check .                          # 28 files already formatted
uv run python -m unittest discover -s tests           # Ran 14 tests ... OK
```

CrewAI (from `crewai-py/`):

```
uv sync
uv run ruff check .                                   # All checks passed!
uv run ruff format --check .                          # 25 files already formatted
uv run python -m unittest discover -s tests           # Ran 21 tests ... OK
```

Real-LLM runners need `OPENROUTER_API_KEY` and were not run; see each track's README.
