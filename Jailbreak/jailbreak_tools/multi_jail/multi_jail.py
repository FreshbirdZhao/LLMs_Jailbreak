#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Jailbreak.jailbreak_tools.loader import Loader
from Jailbreak.jailbreak_tools.multi_jail.result_writer import MultiTurnResultWriter
from Jailbreak.jailbreak_tools.multi_jail.runner import MultiTurnCaseRunner
from Jailbreak.jailbreak_tools.multi_jail.runtime import (
    ResumeTracker,
    autosave_loop,
    emit_progress,
    finish_progress,
    run_task_queue,
)
from Jailbreak.jailbreak_tools.single_jail.model_tester import MultiTurnModelTester


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="多轮越狱测试执行器")
    parser.add_argument("--models", nargs="+", required=True, help="待测试模型名列表")
    parser.add_argument("--datasets", nargs="+", required=True, help="待测试数据集路径列表")
    parser.add_argument("--models-config", default="models.yaml")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--judge-mode", default="non_refusal", choices=["non_refusal"])
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--autosave-interval", type=int, default=10)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--enable-defense", action="store_true", help="启用输入/交互/输出三层防御")
    parser.add_argument("--defense-config", default=None, help="防御配置文件路径（YAML）")
    parser.add_argument("--defense-archive-format", choices=["jsonl", "sqlite"], default="jsonl")
    return parser


def _validate_dataset(path: str) -> list[dict]:
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"数据集不存在: {path}")
    cases = Loader().load(str(dataset_path))
    if not cases:
        raise ValueError(f"数据集为空: {path}")
    return cases


def _build_output_path(output_dir: str, model_names: list[str], dataset: str) -> Path:
    safe_models = "_".join(name.replace("/", "_").replace(":", "_") for name in model_names)
    dataset_name = Path(dataset).stem.lower().replace(" ", "_")
    return Path(output_dir) / f"{safe_models}_{dataset_name}_multi_turn.jsonl"


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    tester = MultiTurnModelTester(models_config_path=args.models_config, timeout=args.timeout)
    try:
        models = tester.get_models(args.models)
        dataset_cases = {dataset: _validate_dataset(dataset) for dataset in args.datasets}
        total = sum(len(cases) * len(models) for cases in dataset_cases.values())
        tracker = ResumeTracker(total=total)
        writers: dict[str, MultiTurnResultWriter] = {}
        autosave_tasks: list[asyncio.Task] = []
        stop_event = asyncio.Event()

        try:
            for dataset in args.datasets:
                output_path = _build_output_path(args.output_dir, args.models, dataset)
                writer = MultiTurnResultWriter(output_path)
                writers[dataset] = writer
                if args.resume:
                    tracker.completed_pairs.update(MultiTurnResultWriter.load_completed_pairs(output_path))
                if args.autosave_interval > 0:
                    autosave_tasks.append(asyncio.create_task(autosave_loop(writer, args.autosave_interval, stop_event)))

            defense_engine = None
            if args.enable_defense:
                defense_engine = tester.build_defense_engine(args.defense_config, args.defense_archive_format)
            runner = MultiTurnCaseRunner(
                model_caller=tester.call_model,
                max_rounds=args.max_rounds,
                defense_engine=defense_engine,
                defense_enabled=args.enable_defense,
            )

            progress_lock = asyncio.Lock()
            tasks = []
            for dataset in args.datasets:
                for model in models:
                    for case in dataset_cases[dataset]:
                        tasks.append(
                            {
                                "dataset": dataset,
                                "writer": writers[dataset],
                                "model": model,
                                "case": case,
                                "model_name": model["name"],
                                "test_id": case["id"],
                            }
                        )

            async def worker_fn(task: dict) -> str:
                result = await runner.run_case(task["model"], task["case"])
                await task["writer"].write_async(result)
                async with progress_lock:
                    emit_progress(tracker.progress_line(result["final_status"]))
                return result["final_status"]

            before_skipped = tracker.completed
            await run_task_queue(tasks=tasks, concurrency=args.concurrency, tracker=tracker, worker_fn=worker_fn)
            skipped_delta = tracker.stats["skipped"]
            if skipped_delta:
                async with progress_lock:
                    emit_progress(tracker.progress_line("skipped"))
        finally:
            stop_event.set()
            if autosave_tasks:
                await asyncio.gather(*autosave_tasks, return_exceptions=True)
            for writer in writers.values():
                await writer.fsync_async()
                writer.close()
            finish_progress()

        print(
            f"total={tracker.total} skipped={tracker.stats['skipped']} success={tracker.stats['success']} "
            f"blocked={tracker.stats['blocked']} refused={tracker.stats['refused']} error={tracker.stats['error']}"
        )
    finally:
        await tester.aclose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
