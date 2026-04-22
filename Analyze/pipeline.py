"""End-to-end record loading and judging pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from Analyze.schema import JudgeDecision


_CHECKPOINT_FILE = "resume_checkpoint.json"
_PARTIAL_ROWS_FILE = "records.partial.jsonl"


def _extract_response_text(rec: dict[str, Any]) -> str:
    conversation = list(rec.get("conversation", []) or [])
    for item in reversed(conversation):
        if not isinstance(item, dict):
            continue
        text = str(item.get("output_response", "") or "").strip()
        if text:
            return text
    return str(rec.get("response", "") or "").strip()


def _iter_jsonl_records(input_dir: str | Path):
    base = Path(input_dir)
    file_paths = [base] if base.is_file() else sorted(base.glob("*.jsonl"))
    for file_path in file_paths:
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


def _decision_fields(decision: JudgeDecision) -> dict[str, Any]:
    payload = decision.to_dict()
    payload.pop("raw_judge_output", None)
    return payload


def evaluate_records(
    input_dir: str | Path,
    base_judge: Any,
    policy_judge: Any,
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
        response = _extract_response_text(rec)
        if hasattr(base_judge, "judge_record"):
            extracted_response = str(getattr(base_judge, "extract_response_text", lambda value: "")(rec) or "")
        else:
            extracted_response = response
        source_file = str(rec.get("source_file") or rec.get("__source_file") or "unknown")

        if hasattr(base_judge, "judge_record"):
            base_decision = base_judge.judge_record(rec)
            final_decision = base_decision if policy_judge is None else policy_judge.judge(base_decision, extracted_response)
        else:
            base_decision = base_judge.judge(response)
            final_decision = base_decision if policy_judge is None else policy_judge.judge(base_decision, response)

        analysis_group = str(rec.get("attack_dimension", "") or "").strip()
        if not analysis_group:
            analysis_group = source_file or "unknown"

        row = {
            "model_name": model_name,
            "attack_type": attack_type,
            "attack_dimension": str(rec.get("attack_dimension", "") or ""),
            "source_file": source_file,
            "analysis_group": analysis_group,
            "category": str(rec.get("category", "unknown") or "unknown"),
            "prompt": str(rec.get("prompt", "") or ""),
            "response": extracted_response or response,
        }
        row.update(_decision_fields(final_decision))
        rows.append(row)

        if partial_rows_path is not None and checkpoint_path is not None:
            _append_partial_row(partial_rows_path, row)
            _write_checkpoint(checkpoint_path, idx)

        if progress_callback:
            progress_callback(idx, total)

    if checkpoint_path is not None and checkpoint_path.exists():
        checkpoint_path.unlink()

    return pd.DataFrame(rows)
