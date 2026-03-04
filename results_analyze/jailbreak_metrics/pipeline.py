"""End-to-end record loading and judging pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from results_analyze.jailbreak_metrics.schema import JudgeDecision


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
                    yield obj


def evaluate_records(
    input_dir: str | Path,
    base_judge: Any,
    policy_judge: Any,
    progress_callback: Callable[[int, int], None] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    records = list(_iter_jsonl_records(input_dir)) if progress_callback else _iter_jsonl_records(input_dir)
    total = len(records) if progress_callback else 0
    for idx, rec in enumerate(records, start=1):
        model_name = str(rec.get("model_name", "unknown") or "unknown")
        attack_type = str(rec.get("attack_type", "unknown") or "unknown")
        response = str(rec.get("response", "") or "")

        base_decision: JudgeDecision = base_judge.judge(response)
        final_decision: JudgeDecision = policy_judge.judge(base_decision, response)

        rows.append(
            {
                "model_name": model_name,
                "attack_type": attack_type,
                "category": str(rec.get("category", "unknown") or "unknown"),
                "prompt": str(rec.get("prompt", "") or ""),
                "response": response,
                "is_jailbreak": final_decision.is_jailbreak,
                "risk_level": final_decision.risk_level,
                "evidence_spans": final_decision.evidence_spans,
                "reasoning_tags": final_decision.reasoning_tags,
                "judge_source": final_decision.judge_source,
            }
        )
        if progress_callback:
            progress_callback(idx, total)

    return pd.DataFrame(rows)
