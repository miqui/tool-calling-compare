"""Real-LLM runner (local only): ``python -m tcc_openhands.run <scenario-id> [--variant V]``.

Needs ``OPENROUTER_API_KEY``; the model defaults to ``openrouter/anthropic/claude-sonnet-4.5``
and can be changed with ``TCC_MODEL``. Never used in CI. ``--mock`` runs the scripted LLM instead.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
os.environ.setdefault("LOG_LEVEL", "ERROR")

from tcc_openhands.scenarios import IDS, load  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tcc_openhands.run")
    ap.add_argument("scenario", choices=IDS)
    ap.add_argument("--variant", default=None)
    ap.add_argument("--mock", action="store_true", help="use the scripted LLM (keyless)")
    args = ap.parse_args(argv)

    mod = load(args.scenario)
    result = mod.run(real=not args.mock, variant=args.variant)
    problems = mod.check(result, args.variant)
    print(
        json.dumps(
            {
                "scenario": args.scenario,
                "variant": args.variant,
                "llm": "scripted" if args.mock else os.environ.get("TCC_MODEL", "default"),
                "status": result.status,
                "stopped_by": result.stopped_by,
                "steps": result.steps,
                "attempted_tool_calls": result.attempted_calls,
                "executed_tool_calls": result.executed_calls,
                "final_text": result.final_text,
                "mismatches_vs_expect": problems,
            },
            indent=2,
            default=str,
        )
    )
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
