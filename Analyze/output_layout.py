"""Helpers for consistent analysis output layout and source labeling."""

from __future__ import annotations

from pathlib import Path


def resolve_output_dir(
    output_root: str | Path,
    judge_mode: str,
    *,
    output_run_subdir: str = "",
    analysis_code: str = "",
    multi_turn: bool = False,
) -> Path:
    base = Path(output_root)
    if multi_turn:
        base = base / "multi_turn"
    base = base / judge_mode

    run_subdir = str(output_run_subdir or "").strip() or str(analysis_code or "").strip()
    return base / run_subdir if run_subdir else base


def strip_jsonl_suffix(name: str) -> str:
    return name[:-6] if name.endswith(".jsonl") else name


def normalize_source_label(label: str, source_path: str) -> str:
    raw_label = str(label or "").strip()
    raw_path = Path(str(source_path or "").strip())
    dataset_name = raw_path.name or raw_label

    if "Jailbreak/jailbreak_results" in raw_path.as_posix():
        cleaned = dataset_name
        if cleaned.startswith("jailbreak_"):
            cleaned = cleaned[len("jailbreak_") :]
        return cleaned or strip_jsonl_suffix(raw_label.split(":", 1)[-1])

    if "Defense/defense_results" in raw_path.as_posix():
        mode_dir = raw_path.parent.name
        mode = mode_dir[:-6] if mode_dir.endswith("_layer") else mode_dir
        if mode == "all_layers":
            mode = "all"
        cleaned = dataset_name
        prefix = f"{mode_dir}/"
        label_body = raw_label.split(":", 1)[-1]
        if label_body.startswith(prefix):
            cleaned = label_body[len(prefix) :]
        return f"{cleaned} (defense)_{mode}"

    return raw_label
