from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


def _iter_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _normalize_group(row: dict[str, Any]) -> str:
    for key in ("attack_dimension", "analysis_group", "source_file"):
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return "unknown"


def _flatten_record(row: dict[str, Any]) -> dict[str, Any]:
    triggered_layers = list(row.get("defense_triggered_layers", []) or [])
    enabled_layers = list(row.get("defense_layers_enabled", []) or [])
    return {
        "model_name": str(row.get("model_name", "") or ""),
        "test_id": str(row.get("test_id", "") or ""),
        "category": str(row.get("category", "") or ""),
        "attack_type": str(row.get("attack_type", "") or ""),
        "analysis_group": _normalize_group(row),
        "source_file": str(row.get("source_file", "") or ""),
        "final_status": str(row.get("final_status", "") or ""),
        "defense_enabled": bool(row.get("defense_enabled", False)),
        "defense_blocked": bool(row.get("defense_blocked", False)),
        "defense_final_action": str(row.get("defense_final_action", "allow") or "allow"),
        "defense_final_risk_level": int(row.get("defense_final_risk_level", 0) or 0),
        "defense_pre_action": str(row.get("defense_pre_action", "allow") or "allow"),
        "defense_post_action": str(row.get("defense_post_action", "allow") or "allow"),
        "defense_prompt_changed": bool(row.get("defense_prompt_changed", False)),
        "defense_response_changed": bool(row.get("defense_response_changed", False)),
        "defense_layers_enabled": "|".join(enabled_layers),
        "defense_triggered_layers": "|".join(triggered_layers),
        "triggered_layer_count": len(triggered_layers),
    }


def _build_action_summary(records: list[dict[str, Any]]) -> pd.DataFrame:
    total = len(records)
    counter = Counter(str(row.get("defense_final_action", "allow") or "allow") for row in records)
    rows = []
    for action, count in sorted(counter.items()):
        rows.append(
            {
                "defense_final_action": action,
                "count": count,
                "ratio": count / total if total else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _build_group_metrics(records: list[dict[str, Any]]) -> pd.DataFrame:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[_normalize_group(row)].append(row)

    metric_rows: list[dict[str, Any]] = []
    for group_name, group_rows in sorted(grouped.items()):
        total = len(group_rows)
        action_counter = Counter(str(row.get("defense_final_action", "allow") or "allow") for row in group_rows)
        success_count = sum(1 for row in group_rows if str(row.get("final_status", "")) == "success")
        blocked_count = sum(1 for row in group_rows if bool(row.get("defense_blocked", False)))
        metric_rows.append(
            {
                "analysis_group": group_name,
                "total": total,
                "success_count": success_count,
                "success_rate": success_count / total if total else 0.0,
                "blocked_count": blocked_count,
                "blocked_rate": blocked_count / total if total else 0.0,
                "allow_count": action_counter.get("allow", 0),
                "rewrite_count": action_counter.get("rewrite", 0),
                "block_count": action_counter.get("block", 0),
                "truncate_count": action_counter.get("truncate", 0),
                "redact_count": action_counter.get("redact", 0),
                "replace_count": action_counter.get("replace", 0),
                "prompt_changed_count": sum(1 for row in group_rows if bool(row.get("defense_prompt_changed", False))),
                "response_changed_count": sum(1 for row in group_rows if bool(row.get("defense_response_changed", False))),
            }
        )
    return pd.DataFrame(metric_rows)


def _build_layer_metrics(records: list[dict[str, Any]]) -> pd.DataFrame:
    counter: Counter[tuple[str, str]] = Counter()
    risk_totals: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
    for row in records:
        for item in list(row.get("defense_decision_history", []) or []):
            if not isinstance(item, dict):
                continue
            layer = str(item.get("layer", "") or "").split("_")[0] or "unknown"
            action = str(item.get("action", "allow") or "allow")
            key = (layer, action)
            counter[key] += 1
            risk_totals[key].append(int(item.get("risk_level", 0) or 0))

    rows = []
    for (layer, action), count in sorted(counter.items()):
        risks = risk_totals[(layer, action)]
        rows.append(
            {
                "layer": layer,
                "action": action,
                "count": count,
                "mean_risk_level": sum(risks) / len(risks) if risks else 0.0,
            }
        )
    return pd.DataFrame(rows)


def export_defense_metrics(input_path: str | Path, output_dir: str | Path) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    raw_rows = _iter_jsonl(input_path)
    records = [_flatten_record(row) for row in raw_rows]

    records_df = pd.DataFrame(records)
    action_df = _build_action_summary(raw_rows)
    group_df = _build_group_metrics(raw_rows)
    layer_df = _build_layer_metrics(raw_rows)

    outputs = {
        "defense_records": output_root / "defense_records.csv",
        "defense_action_summary": output_root / "defense_action_summary.csv",
        "defense_group_metrics": output_root / "defense_group_metrics.csv",
        "defense_layer_metrics": output_root / "defense_layer_metrics.csv",
    }
    records_df.to_csv(outputs["defense_records"], index=False)
    action_df.to_csv(outputs["defense_action_summary"], index=False)
    group_df.to_csv(outputs["defense_group_metrics"], index=False)
    layer_df.to_csv(outputs["defense_layer_metrics"], index=False)
    return outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export defense experiment metrics from JSONL results.")
    parser.add_argument("--input", required=True, help="Input JSONL result file path")
    parser.add_argument("--output-dir", required=True, help="Output directory for CSV metrics")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    export_defense_metrics(args.input, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
