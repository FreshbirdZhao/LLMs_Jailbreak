"""CLI for jailbreak metrics analysis pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from results_analyze.jailbreak_metrics.judges.ensemble_judge import HybridJudge
from results_analyze.jailbreak_metrics.judges.keyword_judge import KeywordJudge
from results_analyze.jailbreak_metrics.judges.llm_judge import LLMJudge
from results_analyze.jailbreak_metrics.judges.structured_policy_judge import StructuredPolicyJudge
from results_analyze.jailbreak_metrics.llm_clients import build_llm_client
from results_analyze.jailbreak_metrics.pipeline import evaluate_records
from results_analyze.jailbreak_metrics.plotting import (
    plot_risk_distribution,
    plot_risk_heatmap,
    plot_success_rate,
    plot_uncertainty_overview,
)
from results_analyze.jailbreak_metrics.stats import compute_group_metrics

DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parent / "jailbreak_analyze"


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
    parser.add_argument(
        "--show-progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show per-record judging progress (default: on)",
    )
    args = parser.parse_args(argv)

    output_root = Path(args.output_dir)
    output_dir = output_root / args.judge_mode
    if args.output_run_subdir:
        output_dir = output_dir / args.output_run_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    records_df = evaluate_records(
        input_dir=args.input_dir,
        base_judge=_build_base_judge(args),
        policy_judge=StructuredPolicyJudge(),
        progress_callback=_build_progress_callback() if args.show_progress else None,
    )
    group_df = compute_group_metrics(records_df)

    records_df.to_csv(output_dir / "records.csv", index=False)
    group_df.to_csv(output_dir / "group_metrics.csv", index=False)

    plot_success_rate(group_df, figures_dir)
    plot_risk_distribution(group_df, figures_dir)
    plot_uncertainty_overview(group_df, figures_dir)
    plot_risk_heatmap(group_df, figures_dir)
    return 0


def main() -> int:
    return run_cli()


def _build_progress_callback():
    def _on_progress(done: int, total: int) -> None:
        print(f"\rJudging records: {done}/{total}", end="", file=sys.stderr, flush=True)
        if done >= total:
            print(file=sys.stderr, flush=True)

    return _on_progress


if __name__ == "__main__":
    raise SystemExit(main())
