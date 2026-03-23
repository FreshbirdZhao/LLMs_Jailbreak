#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert surrogate result JSON/JSONL to CSV usable by jailbreak_tools Loader."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from Redteam.redteam_llm.output_naming import build_default_converted_output_path
except ImportError:
    from redteam_llm.output_naming import build_default_converted_output_path


def _clean_prompt(text: Any) -> str:
    if text is None:
        return ""
    prompt = str(text).strip()
    if prompt.startswith("生成失败") and "最终生成文本：" in prompt:
        prompt = prompt.split("最终生成文本：", 1)[1].strip()
    if prompt.startswith("生成失败"):
        return ""
    return prompt


def _extract_records_from_obj(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    source_original = str(obj.get("original_prompt", "")).strip()
    model = str(obj.get("model", "")).strip()
    timestamp = str(obj.get("timestamp", "")).strip()

    records: List[Dict[str, str]] = []

    if isinstance(obj.get("generated_prompts"), list):
        for idx, item in enumerate(obj.get("generated_prompts", []), start=1):
            prompt = _clean_prompt(item)
            if not prompt:
                continue
            records.append(
                {
                    "prompt": prompt,
                    "original_prompt": source_original,
                    "variant_index": str(idx),
                    "model": model,
                    "timestamp": timestamp,
                }
            )
        return records

    prompt = _clean_prompt(obj.get("generated_prompt"))
    if prompt:
        records.append(
            {
                "prompt": prompt,
                "original_prompt": source_original,
                "variant_index": "1",
                "model": model,
                "timestamp": timestamp,
            }
        )
    return records


def _load_records(input_path: Path) -> List[Dict[str, str]]:
    suffix = input_path.suffix.lower()
    all_records: List[Dict[str, str]] = []

    if suffix == ".jsonl":
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict):
                    all_records.extend(_extract_records_from_obj(obj))
        return all_records

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        all_records.extend(_extract_records_from_obj(data))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                all_records.extend(_extract_records_from_obj(item))
    else:
        raise ValueError(f"Unsupported JSON structure in {input_path}")

    return all_records


def convert_surrogate_json_to_csv(input_path: str, output_dir: str, output_name: str | None = None) -> str:
    in_path = Path(input_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if output_name:
        out_path = out_dir / output_name
    else:
        out_path = build_default_converted_output_path(in_path, out_dir)

    records = _load_records(in_path)
    if not records:
        raise ValueError(f"未提取到有效 prompt: {in_path}")

    fields = ["prompt", "original_prompt", "variant_index", "model", "timestamp", "source_file"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for rec in records:
            rec = dict(rec)
            rec["source_file"] = in_path.name
            writer.writerow(rec)

    return str(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert surrogate JSON/JSONL results to jailbreak CSV")
    parser.add_argument("--input", required=True, help="Path to surrogate result JSON or JSONL")
    parser.add_argument(
        "--output-dir",
        default="/home/jellyz/Experiment/Attack_Dataset",
        help="Directory for output CSV",
    )
    parser.add_argument("--output-name", default=None, help="Optional output CSV name")
    args = parser.parse_args()

    out = convert_surrogate_json_to_csv(args.input, args.output_dir, args.output_name)
    print(f"转换完成: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
