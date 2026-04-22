from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_ENABLED_LAYERS = ["input", "interaction", "output"]
DEFAULT_INPUT_CONFIG = {"block_threshold": 65, "rewrite_threshold": 25}
DEFAULT_INTERACTION_CONFIG = {"block_risk": 65, "warning_risk": 30, "max_round": 3}
DEFAULT_OUTPUT_CONFIG = {
    "archive_path": "Jailbreak/jailbreak_results/defense_audit.jsonl",
    "archive_format": "jsonl",
}


def load_defense_config(path: str | None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled_layers": list(DEFAULT_ENABLED_LAYERS),
        "input": dict(DEFAULT_INPUT_CONFIG),
        "interaction": dict(DEFAULT_INTERACTION_CONFIG),
        "output": dict(DEFAULT_OUTPUT_CONFIG),
    }
    if not path:
        return defaults

    p = Path(path)
    if not p.exists():
        return defaults

    with p.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    for k, v in loaded.items():
        if isinstance(v, dict) and isinstance(defaults.get(k), dict):
            defaults[k].update(v)
        else:
            defaults[k] = v
    return defaults
