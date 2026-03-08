#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multi.py —— 最简多数据集测试入口

复用：
- loader.Loader：数据集格式/内容校验
- single_jail.ModelTester：实际测试执行
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

try:
    from loader import Loader
    from single_jail import ModelTester
except ImportError:
    from Jailbreak.jailbreak_tools.loader import Loader
    from Jailbreak.jailbreak_tools.single_jail import ModelTester


def _validate_dataset(path: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"数据集不存在: {path}")
    cases = Loader().load(str(p))
    if not cases:
        raise ValueError(f"数据集为空: {path}")


async def _run_one_dataset(args: argparse.Namespace, dataset: str) -> None:
    tester = ModelTester(
        args.models_config,
        args.timeout,
        concurrency=args.concurrency,
        retry_limit=args.retry_limit,
        autosave_interval=args.autosave_interval,
        resume=args.resume,
        retry_backoff_base=args.retry_backoff_base,
        retry_backoff_cap=args.retry_backoff_cap,
        enable_defense=args.enable_defense,
        defense_config_path=args.defense_config,
        defense_archive_format=args.defense_archive_format,
    )
    tester.setup_output(
        out_dir=args.output_dir,
        model_names=args.models,
        dataset_path=dataset,
        scale=args.scale,
        dataset_name_for_output=None,
    )
    await tester.run_tests(args.models, dataset)


async def main() -> None:
    parser = argparse.ArgumentParser(description="多数据集越狱测试执行器（最简版）")
    parser.add_argument("--models", nargs="+", required=True, help="待测试模型名列表")
    parser.add_argument("--datasets", nargs="+", required=True, help="待测试数据集路径列表")
    parser.add_argument("--models-config", default="models.yaml")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--scale", default="full", help="测试规模: full 或 partial")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--retry-limit", type=int, default=3)
    parser.add_argument("--autosave-interval", type=int, default=10, help="定时落盘间隔（秒，0=关闭）")
    parser.add_argument("--resume", action="store_true", help="断点续跑")
    parser.add_argument("--retry-backoff-base", type=float, default=2.0)
    parser.add_argument("--retry-backoff-cap", type=float, default=30.0)
    parser.add_argument("--enable-defense", action="store_true", help="启用三层防御")
    parser.add_argument("--defense-config", default=None, help="防御配置 YAML 路径")
    parser.add_argument("--defense-archive-format", choices=["jsonl", "sqlite"], default="jsonl")
    args = parser.parse_args()

    for dataset in args.datasets:
        _validate_dataset(dataset)

    for idx, dataset in enumerate(args.datasets, start=1):
        print(f"\n===== [{idx}/{len(args.datasets)}] 开始数据集: {dataset} =====")
        await _run_one_dataset(args, dataset)


if __name__ == "__main__":
    asyncio.run(main())
