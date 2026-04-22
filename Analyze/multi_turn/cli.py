"""CLI for multi-turn jailbreak metrics analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from Analyze.cli import (
    DEFAULT_OUTPUT_ROOT,
    _build_base_judge,
    _build_progress_callback,
)
from Analyze.output_layout import resolve_output_dir
from Analyze.multi_turn.pipeline import evaluate_records
from Analyze.plotting import (
    plot_ambiguity_breakdown,
    plot_assistance_vs_harm_matrix,
    plot_label_distribution,
    plot_multi_turn_cumulative_success,
    plot_multi_turn_first_success_distribution,
    plot_refusal_leakage,
    plot_risk_distribution,
    plot_risk_heatmap,
    plot_risk_profile_heatmap,
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
    parser.add_argument("--judge-mode", choices=["paper"], default="paper")
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
    args = parser.parse_args(argv)

    output_dir = resolve_output_dir(
        args.output_dir,
        args.judge_mode,
        output_run_subdir=args.output_run_subdir,
        multi_turn=True,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    records_df = evaluate_records(
        input_dir=args.input_dir,
        base_judge=_build_base_judge(args),
        policy_judge=None,
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
    plot_label_distribution(group_df, figures_dir)
    plot_ambiguity_breakdown(group_df, figures_dir)
    plot_assistance_vs_harm_matrix(group_df, figures_dir)
    plot_risk_profile_heatmap(group_df, figures_dir)
    plot_refusal_leakage(group_df, figures_dir)
    plot_multi_turn_cumulative_success(round_df, figures_dir)
    plot_multi_turn_first_success_distribution(round_df, figures_dir)
    return 0


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
