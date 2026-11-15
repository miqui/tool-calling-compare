"""Real-LLM runner (local only; CI never calls it). Needs OPENROUTER_API_KEY in the environment.

    uv run python -m tcc_crewai.run <scenario-id> [--model anthropic/claude-3.5-haiku]

Uses CrewAI's native OpenAI provider pointed at OpenRouter's OpenAI-compatible endpoint, so the
model id is an OpenRouter id and no litellm extra is needed. Scenarios that gate a tool behind
approval ask on stdin (`ctx.request_human_input`).
"""

import argparse
import os
import sys

from crewai import LLM

from tcc_crewai import scenarios
from tcc_crewai.common import load_scenario

DEFAULT_MODEL = "anthropic/claude-3.5-haiku"
BASE_URL = "https://openrouter.ai/api/v1"


def make_llm(model: str, max_tokens: int | None = None) -> LLM:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set; refusing to run (use the keyless tests instead).")
    extra = {"max_tokens": max_tokens} if max_tokens else {}
    return LLM(
        model=model,
        provider="openai",
        base_url=BASE_URL,
        api_key=key,
        stream=False,
        **extra,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", choices=scenarios.SCENARIO_IDS)
    parser.add_argument("--model", default=os.environ.get("TCC_MODEL", DEFAULT_MODEL))
    args = parser.parse_args(argv)

    module = scenarios.load(args.scenario)
    limits = getattr(module, "real_llm_params", lambda sc: {})

    llm = make_llm(args.model, **limits(load_scenario(args.scenario)))
    run = module.run(llm)
    obs = run.obs
    print(f"scenario={args.scenario} model={args.model}")
    print("tool calls attempted:", obs.attempted())
    for name, mock in run.mocks.items():
        print(f"executed {name}:", mock.executed)
    print("event order:", obs.event_order())
    print("error:", repr(obs.error))
    print("final:", obs.raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
