# tcc-openhands

One example per scenario in [`../scenarios`](../scenarios) using the real
[OpenHands SDK](https://docs.openhands.dev/sdk) (`openhands-sdk` 1.62.0, `openhands-tools`): `Agent`,
`Conversation`, custom `ToolDefinition` / `Action` / `Observation` / `ToolExecutor`, built-in
`FileEditorTool`, event callbacks, `ConfirmRisky` + a security analyzer, `max_iteration_per_run`,
`StuckDetectionThresholds`, `filter_tools_regex`, and `LLM(stream=True)`.

- `src/tcc_openhands/scenarios/<id>.py` - the example (`run()` / `check()`), 18 in total.
- `src/tcc_openhands/harness.py` - JSON scenario -> OpenHands tools, scripted and real LLMs, trace.
- `src/tcc_openhands/run.py` - real-LLM runner (OpenRouter), local only.
- `tests/` - keyless `unittest` tests; the SDK `Agent`/`Conversation` is real, only the LLM is a
  scripted subclass of `openhands.sdk.testing.TestLLM` that follows `mock_llm_script`.
- [`SUPPORT.md`](SUPPORT.md) - partial/unsupported features and why.

## Run manually

```sh
cd openhands-py
uv sync
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests
```

Real output of the last three on this checkout:

```
All checks passed!
27 files already formatted
Ran 14 tests ... OK
```

One scenario with the scripted LLM (no key):

```sh
uv run python -m tcc_openhands.run weather-lookup --mock
```

```json
{
  "scenario": "weather-lookup",
  "llm": "scripted",
  "status": "finished",
  "stopped_by": "final_answer",
  "steps": 2,
  "executed_tool_calls": [{"name": "get_weather", "arguments": {"city": "Paris"}}],
  "final_text": "It is 18C and cloudy in Paris.",
  "mismatches_vs_expect": []
}
```

(abridged: `variant` and `attempted_tool_calls` fields omitted.)

Real-LLM mode needs `OPENROUTER_API_KEY` (optionally `TCC_MODEL`); without it the runner refuses:

```sh
uv run python -m tcc_openhands.run weather-lookup
# OPENROUTER_API_KEY is not set (real-LLM runs are local only)
```

A real OpenRouter run has **not** been executed (no key was available when this was written).
