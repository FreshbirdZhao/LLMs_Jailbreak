"""CLI for multi-turn jailbreak metrics analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from Analyze.cli import (
    DEFAULT_OUTPUT_ROOT,
    _build_base_judge,
    _build_progress_callback,
    _load_source_alias_map,
    _persist_source_manifest,
)
from Analyze.judges.structured_policy_judge import StructuredPolicyJudge
from Analyze.output_layout import resolve_output_dir
from Analyze.multi_turn.pipeline import evaluate_records
from Analyze.plotting import (
    plot_multi_turn_cumulative_success,
    plot_multi_turn_first_success_distribution,
    plot_risk_distribution,
    plot_risk_heatmap,
    plot_success_rate,
    plot_uncertainty_overview,
)
from Analyze.stats import compute_group_metrics, compute_multi_turn_round_metrics


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze multi-turn jailbreak JSONL results with modular judges")
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

    output_dir = resolve_output_dir(
        args.output_dir,
        args.judge_mode,
        output_run_subdir=args.output_run_subdir,
        analysis_code=args.analysis_code,
        multi_turn=True,
    )
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
    round_df = compute_multi_turn_round_metrics(records_df)

    records_df.to_csv(output_dir / "records.csv", index=False)
    group_df.to_csv(output_dir / "group_metrics.csv", index=False)
    round_df.to_csv(output_dir / "multi_turn_round_metrics.csv", index=False)

    plot_success_rate(group_df, figures_dir)
    plot_risk_distribution(group_df, figures_dir)
    plot_uncertainty_overview(group_df, figures_dir)
    plot_risk_heatmap(group_df, figures_dir)
    plot_multi_turn_cumulative_success(round_df, figures_dir)
    plot_multi_turn_first_success_distribution(round_df, figures_dir)
    _persist_source_manifest(args, output_dir)
    return 0


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
