from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict

_TIMESTAMP_COUNTERS: Dict[str, int] = {}


def sanitize_output_stem(name: str) -> str:
    sanitized = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", name.strip(), flags=re.UNICODE)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "results"


def build_default_single_output_path(output_dir: str | Path) -> Path:
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%d%H%M")
    counter = _TIMESTAMP_COUNTERS.get(timestamp, 0)
    while True:
        suffix = "" if counter == 0 else f"_{counter:02d}"
        candidate = base_dir / f"redteam_results_{timestamp}{suffix}.jsonl"
        if not candidate.exists():
            _TIMESTAMP_COUNTERS[timestamp] = counter + 1
            return candidate
        counter += 1


def build_default_batch_output_path(input_path: str | Path, output_dir: str | Path) -> Path:
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    input_stem = sanitize_output_stem(Path(input_path).stem)
    counter = 0
    while True:
        suffix = "" if counter == 0 else f"_{counter:02d}"
        candidate = base_dir / f"redteam_{input_stem}{suffix}.jsonl"
        if not candidate.exists():
            return candidate
        counter += 1


def build_default_converted_output_path(input_path: str | Path, output_dir: str | Path) -> Path:
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    input_stem = sanitize_output_stem(Path(input_path).stem)
    counter = 0
    while True:
        suffix = "" if counter == 0 else f"_{counter:02d}"
        candidate = base_dir / f"{input_stem}{suffix}.csv"
        if not candidate.exists():
            return candidate
        counter += 1
