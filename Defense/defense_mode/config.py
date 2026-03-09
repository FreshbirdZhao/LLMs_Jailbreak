from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_defense_config(path: str | None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled_layers": ["input", "interaction", "output"],
        "input": {"block_threshold": 80, "rewrite_threshold": 40},
        "interaction": {"block_risk": 80, "warning_risk": 40, "max_round": 3},
        "output": {"archive_path": "Jailbreak/jailbreak_results/defense_audit.jsonl", "archive_format": "jsonl"},
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

