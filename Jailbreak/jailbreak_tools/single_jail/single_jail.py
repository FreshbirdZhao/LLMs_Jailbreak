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
from Jailbreak.jailbreak_tools.multi_jail.runtime import (
    ResumeTracker,
    autosave_loop,
    emit_progress,
    finish_progress,
    run_task_queue,
)
from Jailbreak.jailbreak_tools.single_jail.judgers import NonRefusalJudge
from Jailbreak.jailbreak_tools.single_jail.model_tester import MultiTurnModelTester


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="单数据集多轮越狱测试执行器")
    parser.add_argument("--models", nargs="+", required=True, help="待测试模型名列表")
    parser.add_argument("--dataset", required=True, help="待测试数据集路径")
    parser.add_argument("--models-config", default="models.yaml")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-rounds", type=int, default=6)
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
    return Path(output_dir) / f"{safe_models}_{dataset_name}_single_turn.jsonl"


async def _run_single_case(model_caller, model: dict, case: dict, judge=None) -> dict:
    judge = judge or NonRefusalJudge()
    response, elapsed, http_status = await model_caller(
        model,
        [{"role": "user", "content": case["prompt"]}],
    )
    judge_result = judge.judge(response)
    success_round = 1 if judge_result.status == "success" else None

    return {
        "model_name": model["name"],
        "test_id": case["id"],
        "test_name": case["name"],
        "category": case.get("category", "unknown"),
        "attack_type": case.get("attack_type", "unknown"),
        "prompt": case["prompt"],
        "response": response,
        "http_status": http_status,
        "elapsed_time": round(float(elapsed), 2),
        "final_status": judge_result.status,
        "success_round": success_round,
        "rounds_used": 1,
        "judge_mode": "non_refusal",
        "judge_model_name": "",
        "judge_final_reason": judge_result.reason,
        "judge_final_confidence": judge_result.confidence,
        "max_rounds": 1,
        "conversation": [
            {
                "round": 1,
                "input_prompt": case["prompt"],
                "user_prompt": case["prompt"],
                "output_response": response,
                "assistant_response": response,
                "elapsed_time": round(float(elapsed), 2),
                "judge_stage": judge_result.stage,
                "judge_status": judge_result.status,
                "judge_reason": judge_result.reason,
                "judge_feedback": {
                    "status": judge_result.status,
                    "reason": judge_result.reason,
                    "stage": judge_result.stage,
                    "model_name": judge_result.model_name,
                    "confidence": judge_result.confidence,
                    "response_type": judge_result.response_type,
                    "failure_point": judge_result.failure_point,
                    "adjustment_goal": judge_result.adjustment_goal,
                    "do_not_repeat": list(judge_result.do_not_repeat),
                    "alignment_to_original_prompt": judge_result.alignment_to_original_prompt,
                },
                "judge_model_name": judge_result.model_name,
                "judge_confidence": judge_result.confidence,
                "defense_action": "allow",
                "defense_risk_level": 0,
                "defense_reasons": [],
                "defense_prompt": case["prompt"],
                "followup_prompt": "",
                "followup_strategy": "",
                "followup_generator_model": "",
                "followup_generation_error": "",
            }
        ],
        "defense_enabled": False,
        "defense_blocked": False,
        "defense_final_action": "allow",
        "defense_final_risk_level": 0,
        "defense_final_reasons": [],
        "planner_model_name": "",
    }


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    cases = _validate_dataset(args.dataset)
    tester = MultiTurnModelTester(models_config_path=args.models_config, timeout=args.timeout)
    models = tester.get_models(args.models)
    output_path = _build_output_path(args.output_dir, args.models, args.dataset)
    writer = MultiTurnResultWriter(output_path)
    tracker = ResumeTracker(total=len(cases) * len(models))
    if args.resume:
        tracker.completed_pairs.update(MultiTurnResultWriter.load_completed_pairs(output_path))
    stop_event = asyncio.Event()
    autosave_task = None
    if args.autosave_interval > 0:
        autosave_task = asyncio.create_task(autosave_loop(writer, args.autosave_interval, stop_event))

    try:
        progress_lock = asyncio.Lock()
        tasks = []
        for model in models:
            for case in cases:
                tasks.append(
                    {
                        "writer": writer,
                        "model": model,
                        "case": case,
                        "model_name": model["name"],
                        "test_id": case["id"],
                    }
                )

        async def worker_fn(task: dict) -> str:
            result = await _run_single_case(tester.call_model, task["model"], task["case"])
            await task["writer"].write_async(result)
            async with progress_lock:
                emit_progress(tracker.progress_line(result["final_status"]))
            return result["final_status"]

        await run_task_queue(tasks=tasks, concurrency=args.concurrency, tracker=tracker, worker_fn=worker_fn)
        if tracker.stats["skipped"]:
            async with progress_lock:
                emit_progress(tracker.progress_line("skipped"))
    finally:
        stop_event.set()
        if autosave_task:
            await asyncio.gather(autosave_task, return_exceptions=True)
        await writer.fsync_async()
        writer.close()
        finish_progress()
        await tester.aclose()

    print(
        f"total={tracker.total} skipped={tracker.stats['skipped']} success={tracker.stats['success']} "
        f"blocked={tracker.stats['blocked']} refused={tracker.stats['refused']} error={tracker.stats['error']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
