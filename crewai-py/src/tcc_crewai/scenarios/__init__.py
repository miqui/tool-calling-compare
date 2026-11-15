"""One module per scenario id: `tcc_crewai.scenarios.<id>` (file names keep the id's hyphens)."""

from importlib import import_module
from pathlib import Path
from types import ModuleType

SCENARIO_IDS = sorted(p.stem for p in Path(__file__).parent.glob("*.py") if p.stem != "__init__")


def load(scenario_id: str) -> ModuleType:
    """Import a scenario module; hyphenated names work through importlib."""
    return import_module(f"{__name__}.{scenario_id}")
