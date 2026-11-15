# crewai-py

CrewAI (Python, `crewai 1.15.41`) track for the scenarios in `../scenarios/*.json`: one module per
scenario in `src/tcc_crewai/scenarios/<id>.py`, run keylessly against a stub `BaseLLM`
(`ScriptedLLM`) that replays each scenario's `mock_llm_script`.

- Tools: `@tool` and `BaseTool` with pydantic `args_schema`.
- Agent: `Agent(max_iter, max_execution_time, tools)`; Task: `Task(output_pydantic=...)`;
  `LLM(max_tokens)` for the truncation scenario.
- Observation: `crewai_event_bus` tool-usage and LLM events.
- Per-scenario verdicts (supported / partial / emulated / n/a) and reasons: [SUPPORT.md](SUPPORT.md).
  `tool-choice-forced` is n/a, `tool-choice-none` and `stuck-loop-detection` are emulated, and
  `max-output-tokens-truncation` is partial.
- Telemetry/tracing are disabled in `tcc_crewai/__init__.py`.

## Run manually

```sh
cd crewai-py
uv sync
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests
```

Real output (last lines; CrewAI emits some deprecation/token-count warnings on stderr):

```
Checked 139 packages in 3ms
All checks passed!
24 files already formatted
Ran 21 tests in 0.304s

OK
```

Real-LLM runner (local only, needs your own `OPENROUTER_API_KEY`; CI never runs it). Without the
key it refuses to start, which is the only output of it I have run:

```sh
uv run python -m tcc_crewai.run weather-lookup --model anthropic/claude-3.5-haiku
# OPENROUTER_API_KEY is not set; refusing to run (use the keyless tests instead).
```

Not verified: any run against a live model.
