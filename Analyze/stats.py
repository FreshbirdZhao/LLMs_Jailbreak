"""Statistical summaries for jailbreak analysis."""

from __future__ import annotations

import math

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
