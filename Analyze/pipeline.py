"""End-to-end record loading and judging pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from Analyze.schema import JudgeDecision


_CHECKPOINT_FILE = "resume_checkpoint.json"
_PARTIAL_ROWS_FILE = "records.partial.jsonl"


def _iter_jsonl_records(input_dir: str | Path):
    base = Path(input_dir)
    for file_path in sorted(base.glob("*.jsonl")):
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    obj.setdefault("__source_file", file_path.name)
                    yield obj


def _load_partial_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _append_partial_row(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_checkpoint(path: Path, processed_count: int) -> None:
    payload = {"processed_count": int(processed_count)}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def evaluate_records(
    input_dir: str | Path,
    base_judge: Any,
    policy_judge: Any,
    source_alias_map: dict[str, str] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
    checkpoint_dir: str | Path | None = None,
    resume: bool = True,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    # Resume requires deterministic ordering and skip counts, so we materialize records.
    materialize_records = progress_callback is not None or checkpoint_dir is not None
    records = list(_iter_jsonl_records(input_dir)) if materialize_records else _iter_jsonl_records(input_dir)
    total = len(records) if progress_callback else 0

    processed_count = 0
    checkpoint_path: Path | None = None
    partial_rows_path: Path | None = None

    if checkpoint_dir is not None:
        out_dir = Path(checkpoint_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = out_dir / _CHECKPOINT_FILE
        partial_rows_path = out_dir / _PARTIAL_ROWS_FILE

        if resume:
            rows = _load_partial_rows(partial_rows_path)
            processed_count = len(rows)
            if checkpoint_path.exists():
                try:
                    saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                    processed_count = min(processed_count, int(saved.get("processed_count", processed_count)))
                    rows = rows[:processed_count]
                except Exception:
                    pass
        else:
            if checkpoint_path.exists():
                checkpoint_path.unlink()
            if partial_rows_path.exists():
                partial_rows_path.unlink()

    for idx, rec in enumerate(records, start=1):
        if idx <= processed_count:
            if progress_callback:
                progress_callback(idx, total)
            continue

        model_name = str(rec.get("model_name", "unknown") or "unknown")
        attack_type = str(rec.get("attack_type", "unknown") or "unknown")
        response = str(rec.get("response", "") or "")
        raw_source_file = str(rec.get("source_file") or rec.get("__source_file") or "unknown")
        source_file = source_alias_map.get(raw_source_file, raw_source_file) if source_alias_map else raw_source_file

        base_decision: JudgeDecision = base_judge.judge(response)
        final_decision: JudgeDecision = policy_judge.judge(base_decision, response)

        row = {
            "model_name": model_name,
            "attack_type": attack_type,
            "source_file": source_file,
            "category": str(rec.get("category", "unknown") or "unknown"),
            "prompt": str(rec.get("prompt", "") or ""),
            "response": response,
            "is_jailbreak": final_decision.is_jailbreak,
            "risk_level": final_decision.risk_level,
            "evidence_spans": final_decision.evidence_spans,
            "reasoning_tags": final_decision.reasoning_tags,
            "judge_source": final_decision.judge_source,
        }
        rows.append(row)

        if partial_rows_path is not None and checkpoint_path is not None:
            _append_partial_row(partial_rows_path, row)
            _write_checkpoint(checkpoint_path, idx)

        if progress_callback:
            progress_callback(idx, total)

    if checkpoint_path is not None and checkpoint_path.exists():
        checkpoint_path.unlink()

    return pd.DataFrame(rows)
