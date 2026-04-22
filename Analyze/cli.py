"""CLI for jailbreak metrics analysis pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from Analyze.judges.final_judge import FinalJudge
from Analyze.output_layout import resolve_output_dir
from Analyze.pipeline import evaluate_records
from Analyze.plotting import (
    plot_ambiguity_breakdown,
    plot_assistance_vs_harm_matrix,
    plot_dimension_priority_quadrants,
    plot_dimension_profile_panel,
    plot_dimension_risk_heatmap,
    plot_dimension_success_ranking,
    plot_dangerous_success_rate,
    plot_high_risk_ratio,
    plot_high_risk_vs_success,
    plot_label_distribution,
    plot_refusal_leakage,
    plot_risk_distribution,
    plot_risk_profile_heatmap,
    plot_uncertainty_overview,
)
from Analyze.stats import compute_group_metrics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "Results"


def _build_base_judge(args):
    return FinalJudge()


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze jailbreak JSONL results with modular judges")
    parser.add_argument("--input-dir", required=True, help="Directory or single .jsonl file containing results")
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

    records_df.to_csv(output_dir / "records.csv", index=False)
    group_df.to_csv(output_dir / "group_metrics.csv", index=False)
    export_representative_cases(records_df, output_dir / "representative_cases.csv")

    plot_dangerous_success_rate(group_df, figures_dir)
    plot_risk_distribution(group_df, figures_dir)
    plot_uncertainty_overview(group_df, figures_dir)
    plot_high_risk_ratio(group_df, figures_dir)
    plot_high_risk_vs_success(group_df, figures_dir)
    plot_dimension_success_ranking(group_df, figures_dir)
    plot_dimension_risk_heatmap(group_df, figures_dir)
    plot_dimension_profile_panel(group_df, figures_dir)
    plot_dimension_priority_quadrants(group_df, figures_dir)
    plot_label_distribution(group_df, figures_dir)
    plot_ambiguity_breakdown(group_df, figures_dir)
    plot_assistance_vs_harm_matrix(group_df, figures_dir)
    plot_risk_profile_heatmap(group_df, figures_dir)
    plot_refusal_leakage(group_df, figures_dir)
    return 0


def main() -> int:
    return run_cli()


def _build_progress_callback():
    def _on_progress(done: int, total: int) -> None:
        print(f"\rJudging records: {done}/{total}", end="", file=sys.stderr, flush=True)
        if done >= total:
            print(file=sys.stderr, flush=True)

    return _on_progress

def export_representative_cases(records_df, output_path: Path) -> Path:
    columns = [
        "analysis_group",
        "category",
        "is_jailbreak",
        "risk_level",
        "prompt",
        "response",
        "reasoning_tags",
        "source_file",
        "attack_dimension",
        "model_name",
    ]
    if records_df.empty:
        records_df.reindex(columns=columns).to_csv(output_path, index=False)
        return output_path

    work = records_df.copy()
    work["sort_bucket"] = work["is_jailbreak"].map({"yes": 0, "uncertain": 1, "no": 2}).fillna(3)
    work = work.sort_values(by=["sort_bucket", "risk_level"], ascending=[True, False])

    selected = pd.concat(
        [
            work[work["is_jailbreak"] == "yes"].head(10),
            work[work["is_jailbreak"] == "uncertain"].head(10),
            work[work["is_jailbreak"] == "no"].head(10),
        ],
        ignore_index=True,
    ).drop_duplicates(subset=["prompt", "response"])
    selected.reindex(columns=columns).to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    raise SystemExit(main())
