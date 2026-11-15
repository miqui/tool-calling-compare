"""One OpenHands SDK example per scenario; module file name == scenario id.

Each module exposes ``ID``, ``SCENARIO``, ``run(real=False, variant=None) -> RunResult`` and
``check(result, variant=None) -> list[str]`` (empty list == matches the scenario's ``expect``).
File names contain hyphens, so load them with :func:`load`.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

IDS = sorted(p.stem for p in Path(__file__).parent.glob("*.py") if not p.stem.startswith("_"))


def load(scenario_id: str) -> ModuleType:
    if scenario_id not in IDS:
        raise KeyError(f"unknown scenario {scenario_id!r}; known: {', '.join(IDS)}")
    return importlib.import_module(f"{__name__}.{scenario_id}")
