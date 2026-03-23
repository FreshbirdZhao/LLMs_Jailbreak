"""Statistical summaries for jailbreak analysis."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd


_Z_95 = 1.959963984540054


def _wilson_ci(successes: int, total: int, z: float = _Z_95) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2 * total)) / denom
    spread = z * math.sqrt((p * (1 - p) + (z * z) / (4 * total)) / total) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))


def _records_from_df(df: pd.DataFrame) -> list[dict]:
    to_dict = getattr(df, "to_dict", None)
    if callable(to_dict):
        try:
            return list(to_dict(orient="records"))
        except TypeError:
            pass
    rows = getattr(df, "_rows", None)
    if rows is not None:
        return list(rows)
    raise TypeError("Unsupported dataframe type for record extraction")


def _coerce_round_number(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if math.isnan(value) or not value.is_integer():
            return None
        coerced = int(value)
        return coerced if coerced > 0 else None
    return None


def _extract_round_result_labels(row: dict) -> list[str]:
    evaluated = list(row.get("round_evaluated_is_jailbreak", []) or [])
    if evaluated:
        return [str(value or "") for value in evaluated]

    raw_statuses = list(row.get("round_judge_statuses", []) or [])
    labels: list[str] = []
    for status in raw_statuses:
        labels.append("yes" if status == "success" else "no")
    return labels


def _first_yes_round(labels: list[str]) -> int | None:
    for idx, label in enumerate(labels, start=1):
        if label == "yes":
            return idx
    return None


def _extract_first_success_round(row: dict) -> int | None:
    first_success_round = _coerce_round_number(row.get("first_success_round_from_analysis"))
    if first_success_round is not None:
        return first_success_round
    first_success_round = _coerce_round_number(row.get("first_success_round_from_judge"))
    if first_success_round is not None:
        return first_success_round
    return _first_yes_round(_extract_round_result_labels(row))


def compute_group_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        cols = [
            "source_file",
            "total",
            "yes_count",
            "uncertain_count",
            "success_rate",
            "success_variance",
            "ci95_low",
            "ci95_high",
        ] + [f"risk_{i}_ratio" for i in range(5)]
        return pd.DataFrame(columns=cols)

    work = df.copy()
    work["yes_flag"] = (work["is_jailbreak"] == "yes").astype(int)
    work["uncertain_flag"] = (work["is_jailbreak"] == "uncertain").astype(int)
    if "source_file" not in work.columns:
        work["source_file"] = "unknown"
    work["source_file"] = work["source_file"].astype(str).replace("", "unknown")

    grouped = (
        work.groupby(["source_file"], dropna=False)
        .agg(total=("is_jailbreak", "size"), yes_count=("yes_flag", "sum"), uncertain_count=("uncertain_flag", "sum"))
        .reset_index()
    )

    grouped["success_rate"] = grouped["yes_count"] / grouped["total"].replace(0, np.nan)
    grouped["success_rate"] = grouped["success_rate"].fillna(0.0)
    grouped["success_variance"] = grouped["success_rate"] * (1.0 - grouped["success_rate"])

    cis = grouped.apply(lambda r: _wilson_ci(int(r["yes_count"]), int(r["total"])), axis=1)
    grouped["ci95_low"] = [x[0] for x in cis]
    grouped["ci95_high"] = [x[1] for x in cis]

    risk_counts = (
        work.groupby(["source_file", "risk_level"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=[0, 1, 2, 3, 4], fill_value=0)
        .reset_index()
    )
    for i in range(5):
        risk_counts[f"risk_{i}_ratio"] = risk_counts[i] / risk_counts[[0, 1, 2, 3, 4]].sum(axis=1).replace(0, np.nan)
        risk_counts[f"risk_{i}_ratio"] = risk_counts[f"risk_{i}_ratio"].fillna(0.0)

    risk_ratio_cols = ["source_file"] + [f"risk_{i}_ratio" for i in range(5)]
    merged = grouped.merge(risk_counts[risk_ratio_cols], on=["source_file"], how="left")
    return merged


def compute_multi_turn_round_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = _records_from_df(df)
    if not rows:
        cols = [
            "source_file",
            "round",
            "total_records",
            "attempt_count",
            "success_count",
            "first_success_count",
            "round_success_rate",
            "cumulative_success_count",
            "cumulative_success_rate",
        ]
        return pd.DataFrame(columns=cols)

    grouped_records: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        source_file = str(row.get("source_file", "unknown") or "unknown")
        grouped_records[source_file].append(row)

    metric_rows: list[dict[str, float | int | str]] = []
    for source_file, source_rows in grouped_records.items():
        total_records = len(source_rows)
        max_round = 0
        for row in source_rows:
            labels = _extract_round_result_labels(row)
            max_round = max(max_round, len(labels))
            rounds_used = _coerce_round_number(row.get("rounds_used"))
            if rounds_used is not None:
                max_round = max(max_round, rounds_used)

        if max_round <= 0:
            continue

        first_success_rounds = []
        for row in source_rows:
            first_success_round = _extract_first_success_round(row)
            if first_success_round is not None:
                first_success_rounds.append(first_success_round)

        for round_number in range(1, max_round + 1):
            attempt_count = 0
            success_count = 0
            first_success_count = 0

            for row in source_rows:
                labels = _extract_round_result_labels(row)
                if len(labels) >= round_number:
                    attempt_count += 1
                    if labels[round_number - 1] == "yes":
                        success_count += 1

                first_success_round = _extract_first_success_round(row)
                if first_success_round == round_number:
                    first_success_count += 1

            cumulative_success_count = sum(1 for value in first_success_rounds if value <= round_number)
            metric_rows.append(
                {
                    "source_file": source_file,
                    "round": round_number,
                    "total_records": total_records,
                    "attempt_count": attempt_count,
                    "success_count": success_count,
                    "first_success_count": first_success_count,
                    "round_success_rate": (success_count / attempt_count) if attempt_count else 0.0,
                    "cumulative_success_count": cumulative_success_count,
                    "cumulative_success_rate": (cumulative_success_count / total_records) if total_records else 0.0,
                }
            )

    metric_rows.sort(key=lambda row: (str(row["source_file"]), int(row["round"])))
    return pd.DataFrame(metric_rows)
