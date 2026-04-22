"""Helpers for consistent analysis output layout and source labeling."""

from __future__ import annotations

from pathlib import Path


def normalize_judge_mode_label(judge_mode: str) -> str:
    mode = str(judge_mode or "").strip()
    return "final" if mode == "paper" else mode


def resolve_output_dir(
    output_root: str | Path,
    judge_mode: str,
    *,
    output_run_subdir: str = "",
    multi_turn: bool = False,
) -> Path:
    base = Path(output_root)
    if multi_turn:
        base = base / "multi_turn"
    base = base / normalize_judge_mode_label(judge_mode)

    run_subdir = str(output_run_subdir or "").strip()
    return base / run_subdir if run_subdir else base
