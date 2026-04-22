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
from Jailbreak.jailbreak_tools.multi_jail.result_writer import MultiTurnResultWriter, OrderedResultWriter
from Jailbreak.jailbreak_tools.multi_jail.runtime import (
    ResumeTracker,
    autosave_loop,
    emit_progress,
    finish_progress,
    run_task_queue,
)
from Jailbreak.jailbreak_tools.single_jail.judgers import NonRefusalJudge
from Jailbreak.jailbreak_tools.single_jail.model_tester import MultiTurnModelTester
from Defense.defense_mode import DefenseAction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="单数据集多轮越狱测试执行器")
    parser.add_argument("--models", nargs="+", required=True, help="待测试模型名列表")
    parser.add_argument("--dataset", required=True, help="待测试数据集路径")
    parser.add_argument("--models-config", default="models.yaml")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--concurrency", type=int, default=8)
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


async def _run_single_case(
    model_caller,
    model: dict,
    case: dict,
    judge=None,
    defense_engine=None,
    defense_enabled: bool = False,
) -> dict:
    judge = judge or NonRefusalJudge()
    defense_active = bool(defense_enabled and defense_engine is not None)
    enabled_layers: list[str] = []
    if defense_active:
        if getattr(defense_engine, "input_module", None) is not None:
            enabled_layers.append("input")
        if getattr(defense_engine, "interaction_module", None) is not None:
            enabled_layers.append("interaction")
        if getattr(defense_engine, "output_module", None) is not None:
            enabled_layers.append("output")
    prompt_to_send = case["prompt"]
    response = ""
    visible_response = ""
    raw_response = ""
    elapsed = 0.0
    http_status = None
    defense_blocked = False
    final_defense_action = "allow"
    final_defense_risk_level = 0
    final_defense_reasons: list[str] = []
    defense_pre_action = "allow"
    defense_post_action = "allow"
    defense_prompt_changed = False
    defense_response_changed = False
    defense_triggered_layers: list[str] = []
    defense_decision_history: list[dict] = []

    defense_context = None
    defense_pre = None
    if defense_active:
        defense_context = defense_engine.build_context_from_case(case=case, model_name=model["name"], round_idx=1)
        defense_pre = defense_engine.apply_pre_call_defense(defense_context)
        if defense_context.sanitized_prompt:
            prompt_to_send = defense_context.sanitized_prompt
            defense_prompt_changed = prompt_to_send != case["prompt"]
        final_defense_action = defense_pre.action.value
        final_defense_risk_level = defense_pre.risk_level
        final_defense_reasons = list(defense_pre.reasons)
        defense_pre_action = defense_pre.action.value
        defense_decision_history = list(getattr(defense_context, "decision_history", []))
        defense_triggered_layers = [
            str(item.get("layer", "")).split("_")[0]
            for item in defense_decision_history
            if str(item.get("action", "allow")) != "allow"
        ]

    if defense_active and (
        not getattr(defense_context, "model_call_allowed", True)
        or defense_pre.action in {DefenseAction.BLOCK, DefenseAction.TRUNCATE}
    ):
        visible_response = defense_pre.rewritten_text or "Request blocked by defense policy."
        raw_response = visible_response
        defense_blocked = True
        judge_result = judge.judge(visible_response)
        final_status = "blocked"
        success_round = None
    else:
        response, elapsed, http_status = await model_caller(
            model,
            [{"role": "user", "content": prompt_to_send}],
        )
        raw_response = response
        visible_response = response

        if defense_active:
            defense_post = defense_engine.apply_post_call_defense(defense_context, response)
            if defense_context.sanitized_response:
                visible_response = defense_context.sanitized_response
                defense_response_changed = visible_response != raw_response
            chosen_decision = defense_post if defense_post.action != DefenseAction.ALLOW else defense_pre
            final_defense_action = chosen_decision.action.value
            final_defense_risk_level = chosen_decision.risk_level
            final_defense_reasons = list(chosen_decision.reasons)
            defense_post_action = defense_post.action.value
            defense_decision_history = list(getattr(defense_context, "decision_history", []))
            defense_triggered_layers = [
                str(item.get("layer", "")).split("_")[0]
                for item in defense_decision_history
                if str(item.get("action", "allow")) != "allow"
            ]

        judge_result = judge.judge(visible_response)
        success_round = 1 if judge_result.status == "success" else None
        final_status = judge_result.status

    return {
        "model_name": model["name"],
        "test_id": case["id"],
        "test_name": case["name"],
        "category": case.get("category", "unknown"),
        "attack_type": case.get("attack_type", "unknown"),
        "attack_dimension": case.get("attack_dimension", ""),
        "attack_method": case.get("attack_method", ""),
        "source_prompt": case.get("source_prompt", ""),
        "source_file": case.get("source_file", ""),
        "origin": case.get("origin", ""),
        "prompt": case["prompt"],
        "response": visible_response,
        "http_status": http_status,
        "elapsed_time": round(float(elapsed), 2),
        "final_status": final_status,
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
                "output_response": visible_response,
                "assistant_response": visible_response,
                "raw_assistant_response": raw_response,
                "elapsed_time": round(float(elapsed), 2),
                "judge_stage": judge_result.stage,
                "judge_status": final_status,
                "judge_reason": judge_result.reason,
                "judge_feedback": {
                    "status": final_status,
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
                "defense_action": final_defense_action,
                "defense_risk_level": final_defense_risk_level,
                "defense_reasons": list(final_defense_reasons),
                "defense_prompt": prompt_to_send,
                "defense_layers_enabled": list(enabled_layers),
                "defense_triggered_layers": list(dict.fromkeys(defense_triggered_layers)),
                "defense_pre_action": defense_pre_action,
                "defense_post_action": defense_post_action,
                "defense_prompt_changed": defense_prompt_changed,
                "defense_response_changed": defense_response_changed,
                "followup_prompt": "",
                "followup_strategy": "",
                "followup_generator_model": "",
                "followup_generation_error": "",
            }
        ],
        "defense_enabled": defense_active,
        "defense_blocked": defense_blocked,
        "defense_layers_enabled": list(enabled_layers),
        "defense_triggered_layers": list(dict.fromkeys(defense_triggered_layers)),
        "defense_pre_action": defense_pre_action,
        "defense_post_action": defense_post_action,
        "defense_final_action": final_defense_action,
        "defense_final_risk_level": final_defense_risk_level,
        "defense_final_reasons": list(final_defense_reasons),
        "defense_prompt_changed": defense_prompt_changed,
        "defense_response_changed": defense_response_changed,
        "defense_decision_history": defense_decision_history,
        "planner_model_name": "",
    }


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    cases = _validate_dataset(args.dataset)
    tester = MultiTurnModelTester(models_config_path=args.models_config, timeout=args.timeout)
    models = tester.get_models(args.models)
    defense_engine = None
    if args.enable_defense:
        defense_engine = tester.build_defense_engine(
            defense_config_path=args.defense_config,
            defense_archive_format=args.defense_archive_format,
        )
    output_path = _build_output_path(args.output_dir, args.models, args.dataset)
    writer = MultiTurnResultWriter(output_path)
    tracker = ResumeTracker(total=len(cases) * len(models))
    if args.resume:
        tracker.completed_pairs.update(MultiTurnResultWriter.load_completed_pairs(output_path))
    completed_indices: set[int] = set()
    stop_event = asyncio.Event()
    autosave_task = None
    if args.autosave_interval > 0:
        autosave_task = asyncio.create_task(autosave_loop(writer, args.autosave_interval, stop_event))

    try:
        progress_lock = asyncio.Lock()
        tasks = []
        for task_index, (model, case) in enumerate((model, case) for model in models for case in cases):
            if tracker.should_skip(model["name"], case["id"]):
                completed_indices.add(task_index)
            tasks.append(
                {
                    "write_index": task_index,
                    "model": model,
                    "case": case,
                    "model_name": model["name"],
                    "test_id": case["id"],
                }
            )
        ordered_writer = OrderedResultWriter(writer, completed_indices=completed_indices)

        async def worker_fn(task: dict) -> str:
            result = await _run_single_case(
                tester.call_model,
                task["model"],
                task["case"],
                defense_engine=defense_engine,
                defense_enabled=args.enable_defense,
            )
            await ordered_writer.write_async(task["write_index"], result)
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
