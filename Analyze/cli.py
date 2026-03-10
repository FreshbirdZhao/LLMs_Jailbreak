"""CLI for jailbreak metrics analysis pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from Analyze.judges.ensemble_judge import HybridJudge
from Analyze.judges.keyword_judge import KeywordJudge
from Analyze.judges.llm_judge import LLMJudge
from Analyze.judges.structured_policy_judge import StructuredPolicyJudge
from Analyze.llm_clients import build_llm_client
from Analyze.pipeline import evaluate_records
from Analyze.plotting import (
    plot_risk_distribution,
    plot_risk_heatmap,
    plot_success_rate,
    plot_uncertainty_overview,
)
from Analyze.stats import compute_group_metrics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "Results"
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "Results" / "directory"


def _strip_jsonl_suffix(name: str) -> str:
    return name[:-6] if name.endswith(".jsonl") else name


def _normalize_source_label(label: str, source_path: str) -> str:
    raw_label = str(label or "").strip()
    raw_path = Path(str(source_path or "").strip())
    dataset_name = raw_path.name or raw_label

    if "Jailbreak/jailbreak_results" in raw_path.as_posix():
        cleaned = dataset_name
        if cleaned.startswith("jailbreak_"):
            cleaned = cleaned[len("jailbreak_") :]
        return cleaned or _strip_jsonl_suffix(raw_label.split(":", 1)[-1])

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
        return f"{cleaned}\n(defense)_{mode}"

    return raw_label


def _build_base_judge(args):
    mode = args.judge_mode
    keyword = KeywordJudge()

    if mode == "keyword":
        return keyword

    llm_client = build_llm_client(
        {
            "provider": args.llm_provider,
            "model": args.llm_model,
            "base_url": args.llm_base_url,
            "api_key": args.llm_api_key,
            "timeout": args.llm_timeout,
            "max_retries": args.llm_max_retries,
            "retry_backoff": args.llm_retry_backoff,
        }
    )
    llm = LLMJudge(client=llm_client)

    if mode == "llm":
        return llm
    return HybridJudge(keyword, llm)


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze jailbreak JSONL results with modular judges")
    parser.add_argument("--input-dir", required=True, help="Directory containing .jsonl files")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_ROOT), help="Root directory to write mode-specific outputs")
    parser.add_argument(
        "--output-run-subdir",
        default="",
        help="Optional run-level subdirectory under mode output dir (e.g. <root>/<mode>/<subdir>)",
    )
    parser.add_argument("--judge-mode", choices=["keyword", "llm", "hybrid"], default="keyword")
    parser.add_argument("--llm-provider", choices=["ollama", "external"], default="ollama")
    parser.add_argument("--llm-model", default="qwen2:latest")
    parser.add_argument("--llm-base-url", default="")
    parser.add_argument("--llm-api-key", default="")
    parser.add_argument("--llm-timeout", type=int, default=30)
    parser.add_argument("--llm-max-retries", type=int, default=2)
    parser.add_argument("--llm-retry-backoff", type=float, default=1.0)
    parser.add_argument(
        "--show-progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show per-record judging progress (default: on)",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume from partial progress if checkpoint files exist (default: on)",
    )
    parser.add_argument("--analysis-code", default="", help="Optional numeric run code used to track source datasets")
    parser.add_argument(
        "--source-manifest-file",
        default="",
        help="Optional TSV file of selected sources: <label>\\t<source_path>\\t<copied_filename>",
    )
    args = parser.parse_args(argv)

    output_root = Path(args.output_dir)
    output_dir = output_root / args.judge_mode
    if args.output_run_subdir:
        output_dir = output_dir / args.output_run_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    source_alias_map = _load_source_alias_map(args.source_manifest_file)

    records_df = evaluate_records(
        input_dir=args.input_dir,
        base_judge=_build_base_judge(args),
        policy_judge=StructuredPolicyJudge(),
        source_alias_map=source_alias_map,
        progress_callback=_build_progress_callback() if args.show_progress else None,
        checkpoint_dir=output_dir,
        resume=args.resume,
    )
    group_df = compute_group_metrics(records_df)

    records_df.to_csv(output_dir / "records.csv", index=False)
    group_df.to_csv(output_dir / "group_metrics.csv", index=False)

    plot_success_rate(group_df, figures_dir)
    plot_risk_distribution(group_df, figures_dir)
    plot_uncertainty_overview(group_df, figures_dir)
    plot_risk_heatmap(group_df, figures_dir)
    _persist_source_manifest(args, output_dir)
    return 0


def main() -> int:
    return run_cli()


def _build_progress_callback():
    def _on_progress(done: int, total: int) -> None:
        print(f"\rJudging records: {done}/{total}", end="", file=sys.stderr, flush=True)
        if done >= total:
            print(file=sys.stderr, flush=True)

    return _on_progress


def _persist_source_manifest(args, output_dir: Path) -> None:
    if not args.source_manifest_file:
        return

    manifest_path = Path(args.source_manifest_file)
    if not manifest_path.exists():
        return

    sources: list[dict[str, str]] = []
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            label, source_path, copied_filename = parts
            sources.append(
                {
                    "label": label,
                    "source_path": source_path,
                    "copied_filename": copied_filename,
                }
            )

    if not sources:
        return

    analysis_code = (args.analysis_code or output_dir.name).strip() or "run_unknown"
    payload = {
        "analysis_code": analysis_code,
        "judge_mode": args.judge_mode,
        "created_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "sources": sources,
    }

    (output_dir / "input_sources.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    source_dir = DEFAULT_SOURCE_ROOT
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / f"{analysis_code}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_source_alias_map(source_manifest_file: str) -> dict[str, str]:
    if not source_manifest_file:
        return {}
    manifest_path = Path(source_manifest_file)
    if not manifest_path.exists():
        return {}

    source_alias_map: dict[str, str] = {}
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            label, source_path, copied_filename = parts
            source_alias_map[copied_filename] = _normalize_source_label(label, source_path)
    return source_alias_map


if __name__ == "__main__":
    raise SystemExit(main())
