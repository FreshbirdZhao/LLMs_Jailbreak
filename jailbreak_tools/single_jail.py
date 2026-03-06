#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jailbreak_test.py —— 高速并发 + 实时保存 + 自动重试队列
⚠ 本文件只负责测试，不做攻击结果判断。
"""

import os
import sys
import yaml
import json
import time
import asyncio
import argparse
import signal
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Set
import httpx
import pandas as pd
from asyncio import Semaphore

# ------------------------------
# 颜色支持（ANSI转义码）
# ------------------------------
class Colors:
    """终端颜色支持"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    @staticmethod
    def success(text):
        return f"{Colors.GREEN}{text}{Colors.RESET}"

    @staticmethod
    def error(text):
        return f"{Colors.RED}{text}{Colors.RESET}"

    @staticmethod
    def warning(text):
        return f"{Colors.YELLOW}{text}{Colors.RESET}"

    @staticmethod
    def info(text):
        return f"{Colors.CYAN}{text}{Colors.RESET}"

    @staticmethod
    def cyan(text):
        return f"{Colors.CYAN}{text}{Colors.RESET}"

    @staticmethod
    def bold(text):
        return f"{Colors.BOLD}{text}{Colors.RESET}"


# ------------------------------
# 数据集加载器
# ------------------------------
try:
    from loader import Loader
except ImportError:
    print("错误：未找到 loader.py")
    sys.exit(1)


# ====================================================
#                 Model Tester（完整增强版）
# ====================================================
class ModelTester:
    """越狱攻击测试执行器（支持高速并发、实时保存、失败自动重试）"""

    # ---------------------------
    # 方案B：快速提取 resume 字段（避免 json.loads 整行）
    # 说明：匹配 JSONL 行中的 "model_name":"..." 与 "test_id":"..."
    # ---------------------------
    _re_model_name = re.compile(r'"model_name"\s*:\s*"((?:\\.|[^"\\])*)"')
    _re_test_id = re.compile(r'"test_id"\s*:\s*"((?:\\.|[^"\\])*)"')

    def __init__(
        self,
        models_config_path: str,
        timeout: int,
        concurrency: int,
        retry_limit: int,
        autosave_interval: int,
        resume: bool,
        retry_backoff_base: float,
        retry_backoff_cap: float,
    ):
        self.models_config = self._load_models_config(models_config_path)

        # ---------------------------
        # httpx 连接池限制（高并发更稳定）
        # ---------------------------
        limits = httpx.Limits(
            max_connections=max(50, concurrency * 4),
            max_keepalive_connections=max(10, concurrency),
        )
        self.client = httpx.AsyncClient(timeout=timeout, limits=limits)

        self.output_jsonl = None
        self._jsonl_fp = None

        # ---------------------------
        # 并发/重试参数（来自 CLI）
        # ---------------------------
        self.concurrency = concurrency
        self.retry_limit = retry_limit
        self.retry_backoff_base = retry_backoff_base
        self.retry_backoff_cap = retry_backoff_cap

        # ---------------------------
        # 定时保存（flush + fsync）间隔（秒）
        # ---------------------------
        self.autosave_interval = autosave_interval
        self._autosave_task = None

        # ---------------------------
        # 断点续跑
        # ---------------------------
        self.resume = resume
        self.completed_pairs: Set[Tuple[str, str]] = set()  # (model_name, test_id)

        # ---------------------------
        # 终端输出锁（解决并发 print 粘连/串行显示问题）
        # ---------------------------
        self._print_lock = asyncio.Lock()
        self._last_progress_line = ""

        # ---------------------------
        # 停止标记（用于信号退出/优雅收尾）
        # ---------------------------
        self._stop = asyncio.Event()

        # ---------------------------
        # 任务队列（提升效率：错误不阻塞整体；重试异步回灌队列）
        # ---------------------------
        self.work_queue: asyncio.Queue = asyncio.Queue()
        self._attempts: Dict[Tuple[str, str], int] = {}  # (model_name, test_id) -> attempts used
        self._done: Set[Tuple[str, str]] = set()         # 已终结（成功保存 or 最终失败丢弃）

        # ---------------------------
        # 统计
        # ---------------------------
        self.total_tests = 0      # 需要完成的“用例数”（跳过已完成的不计入）
        self.counter = 0          # 已终结用例数（成功+最终失败）
        self.error_count = 0      # 最终失败用例数（丢弃不保存）

    # ---------------------------
    # 加载模型配置
    # ---------------------------
    def _load_models_config(self, path: str) -> Dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"错误：模型配置文件不存在：{path}")
            sys.exit(1)

    # ---------------------------
    # 选择用户指定模型
    # ---------------------------
    def _get_models(self, names: List[str]) -> List[Dict]:
        all_models = self.models_config.get("local", []) + self.models_config.get("commercial", [])

        # 加载 API KEY（仅商用模型使用）
        key_path = Path("config/api_keys.yaml")
        api_keys = {}
        if key_path.exists():
            with open(key_path, "r", encoding="utf-8") as f:
                api_keys = yaml.safe_load(f)

        chosen = []
        for m in all_models:
            if m["name"] not in names:
                continue

            if not m.get("model") or not m.get("base_url") or not m.get("type"):
                print(f"⚠ 模型 {m.get('name', '<unknown>')} 配置不完整（需包含 type/model/base_url），跳过")
                continue

            if m.get("type") != "ollama":
                if m["name"] not in api_keys:
                    print(f"⚠ 模型 {m['name']} 缺少 API KEY，跳过")
                    continue
                m["api_key"] = api_keys[m["name"]]["api_key"]

            chosen.append(m)

        return chosen

    # ---------------------------
    # API 调用（Ollama）
    # ---------------------------
    async def _call_ollama(self, model: Dict, prompt: str):
        url = f"{model['base_url']}/api/generate"
        payload = {"model": model["model"], "prompt": prompt, "stream": False}

        start = time.time()
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", ""), time.time() - start, resp.status_code
        except Exception as e:
            return f"错误：{e}", time.time() - start, None

    # ---------------------------
    # API 调用（OpenAI兼容）
    # ---------------------------
    async def _call_openai(self, model: Dict, prompt: str):
        url = f"{model['base_url']}/chat/completions"
        headers = {"Authorization": f"Bearer {model['api_key']}"}
        payload = {"model": model["model"], "messages": [{"role": "user", "content": prompt}]}

        start = time.time()
        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return content, time.time() - start, resp.status_code
        except Exception as e:
            return f"错误：{e}", time.time() - start, None

    # ---------------------------
    # 统一模型调用
    # ---------------------------
    async def _call_model(self, model: Dict, prompt: str):
        if model["type"] == "ollama":
            return await self._call_ollama(model, prompt)
        return await self._call_openai(model, prompt)

    # ---------------------------
    # 并发安全打印（解决日志粘连）
    # ---------------------------
    async def _safe_print(self, msg: str, redraw_progress: bool = True):
        async with self._print_lock:
            if self._last_progress_line:
                print()
            print(msg, flush=True)
            if redraw_progress and self._last_progress_line:
                print(self._last_progress_line, end="", flush=True)

    # ---------------------------
    # 重绘进度条（锁内渲染，避免并发输出乱序）
    # ---------------------------
    async def _render_progress(self, case_id: str, status: str, elapsed: float):
        progress_pct = (self.counter / self.total_tests) * 100 if self.total_tests else 100.0
        progress_bar_length = 30
        filled = int(progress_bar_length * self.counter / self.total_tests) if self.total_tests else progress_bar_length
        bar = "█" * filled + "░" * (progress_bar_length - filled)
        progress = f"[{self.counter}/{self.total_tests}]"

        line = f"\r{Colors.cyan(progress)} {bar} {progress_pct:.1f}% | {case_id} {status} ({round(elapsed,2)}s)"
        self._last_progress_line = line

        async with self._print_lock:
            print(line, end="", flush=True)
            if self.counter >= self.total_tests:
                print()

    # ---------------------------
    # 检查模型是否可用
    # ---------------------------
    async def _check_model(self, model: Dict):
        resp, _, _status = await self._call_model(model, "Hello")
        if str(resp).startswith("错误"):
            await self._safe_print(f"❌ 模型 {model['name']} 不可用：{resp}", redraw_progress=False)
            return False
        await self._safe_print(f"✔ 模型 {model['name']} 可用", redraw_progress=False)
        return True

    # ---------------------------
    # 实时写入 JSONL（核心保障）
    # ---------------------------
    def _write_jsonl(self, record: dict):
        self._jsonl_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._jsonl_fp.flush()

    # ---------------------------
    # 定时保存（强制落盘）
    # ---------------------------
    async def _autosave_loop(self):
        while not self._stop.is_set():
            await asyncio.sleep(self.autosave_interval)
            try:
                if self._jsonl_fp:
                    self._jsonl_fp.flush()
                    os.fsync(self._jsonl_fp.fileno())
            except Exception as e:
                await self._safe_print(f"{Colors.warning('⚠')} autosave 失败：{e}", redraw_progress=True)

    # ---------------------------
    # 方案B：仅对短字段做反转义（避免解析整行）
    # ---------------------------
    def _json_unescape_small(self, s: str) -> str:
        """
        仅对很短的 JSON 字符串片段做反转义。
        用 json.loads 解析 '"...quoted..."'，避免自己处理 \\u 等细节。
        """
        try:
            return json.loads(f'"{s}"')
        except Exception:
            return s.replace(r'\"', '"').replace(r"\\", "\\")

    def _fast_extract_model_and_id(self, line: str):
        """
        从 JSONL 行文本快速提取 (model_name, test_id)，提取失败返回 (None, None)
        """
        m1 = self._re_model_name.search(line)
        if not m1:
            return None, None
        m2 = self._re_test_id.search(line)
        if not m2:
            return None, None

        model_name = self._json_unescape_small(m1.group(1)).strip()
        test_id = self._json_unescape_small(m2.group(1)).strip()
        return model_name, test_id

    # ---------------------------
    # 断点续跑：读取已完成（已保存成功）的 (model_name, test_id)
    # （方案B：不 json.loads 整行，避免 response 超大导致很慢）
    # ---------------------------
    def _load_completed_pairs(self):
        self.completed_pairs = set()
        if not self.output_jsonl:
            return
        path = Path(self.output_jsonl)
        if not path.exists():
            return

        try:
            # buffering 加大一点，读取大文件更快（可选但几乎无副作用）
            with open(path, "r", encoding="utf-8", buffering=1024 * 1024) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    mn, tid = self._fast_extract_model_and_id(line)
                    if mn and tid:
                        self.completed_pairs.add((mn, tid))
        except Exception:
            # 读文件失败就当作没有 resume 数据
            return

    # ---------------------------
    # 重试延迟（指数退避 + 上限）
    # ---------------------------
    def _compute_backoff(self, attempt_no: int) -> float:
        # attempt_no: 1,2,3...
        delay = self.retry_backoff_base * (2 ** (attempt_no - 1))
        return min(delay, self.retry_backoff_cap)

    async def _enqueue_retry_later(self, model: Dict, case: Dict, attempt_no: int):
        delay = self._compute_backoff(attempt_no)
        await asyncio.sleep(delay)
        if self._stop.is_set():
            return
        await self.work_queue.put((model, case))

    # ---------------------------
    # 单条测试执行（仅成功才保存；失败异步重试不阻塞 worker）
    # ---------------------------
    async def _test_one(self, model: Dict, case: Dict):
        model_name = model["name"]
        case_id = case["id"]
        key = (model_name, case_id)

        # 已终结直接跳过（防重复）
        if key in self._done:
            return

        response, elapsed, http_status = await self._call_model(model, case["prompt"])
        is_error = str(response).startswith("错误") or (http_status is None)

        if is_error:
            # 记录尝试次数
            used = self._attempts.get(key, 0) + 1
            self._attempts[key] = used

            if used <= self.retry_limit:
                await self._safe_print(
                    f"{Colors.warning('⚠')} 失败 → 不保存结果，{case_id} 将在 {self._compute_backoff(used):.1f}s 后重试（第{used}次）",
                    redraw_progress=True
                )
                # 不阻塞：丢给延迟任务，worker 立刻继续处理其他 case
                asyncio.create_task(self._enqueue_retry_later(model, case, used))
                return

            # 最终失败：丢弃不保存，但计入“终结”，否则总进度到不了 100%
            self._done.add(key)
            self.counter += 1
            self.error_count += 1
            await self._render_progress(case_id, Colors.error("✗最终失败"), elapsed)
            return

        # 成功：才保存（并删除 retry 字段输出：不再写 retry）
        record = {
            "timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "test_id": case_id,
            "test_name": case["name"],
            "category": case.get("category", "unknown"),
            "attack_type": case.get("attack_type", "unknown"),
            "prompt": case["prompt"],
            "response": response,
            "http_status": http_status,
            "elapsed_time": round(elapsed, 2),
        }
        self._write_jsonl(record)

        self._done.add(key)
        self.counter += 1
        await self._render_progress(case_id, Colors.success("✓完成"), elapsed)

    # ---------------------------
    # worker：从队列取任务执行（提升效率：不按原顺序保存/不因重试阻塞）
    # ---------------------------
    async def _worker(self):
        while not self._stop.is_set():
            try:
                model, case = await asyncio.wait_for(self.work_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # 如果队列空且已完成，允许退出
                if self.counter >= self.total_tests:
                    return
                continue
            try:
                await self._test_one(model, case)
            finally:
                self.work_queue.task_done()

    # ---------------------------
    # 主流程
    # ---------------------------
    async def run_tests(self, model_names: List[str], dataset_path: str):
        # 信号处理：尽量优雅退出并落盘
        def _handle_signal(signum, frame):
            self._stop.set()

        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except Exception:
            pass

        models = self._get_models(model_names)

        loader = Loader()
        test_cases = loader.load(dataset_path)

        # 断点续跑：读取已保存成功的用例
        if self.resume:
            self._load_completed_pairs()

        # 先检查模型
        await self._safe_print("🔍 检查模型可用性…", redraw_progress=False)
        for m in models:
            ok = await self._check_model(m)
            if not ok:
                return
        await self._safe_print("", redraw_progress=False)

        # 组装任务：跳过已完成的 (model_name, test_id)
        to_run: List[Tuple[Dict, Dict]] = []
        for m in models:
            for c in test_cases:
                key = (m["name"], c["id"])
                if self.resume and key in self.completed_pairs:
                    continue
                to_run.append((m, c))

        self.total_tests = len(to_run)
        self.counter = 0
        self.error_count = 0
        self._done = set()
        self._attempts = {}

        await self._safe_print(f"{Colors.info('📌')} 加载 {len(test_cases)} 条测试用例完成", redraw_progress=False)
        if self.resume:
            await self._safe_print(f"{Colors.info('📌')} 断点续跑：跳过已保存成功 {len(self.completed_pairs)} 条 (按 model+id)", redraw_progress=False)
        await self._safe_print(f"{Colors.info('📌')} 将执行 {self.total_tests} 条测试（仅成功才保存，失败异步退避重试）\n", redraw_progress=False)

        # 启动 autosave（强制落盘）
        if self.autosave_interval and self.autosave_interval > 0:
            self._autosave_task = asyncio.create_task(self._autosave_loop())

        try:
            # 入队（不要求顺序）
            for m, c in to_run:
                await self.work_queue.put((m, c))

            # 启动 worker 池
            workers = [asyncio.create_task(self._worker()) for _ in range(max(1, self.concurrency))]

            # 等待所有队列任务（包含后续重试回灌）完成
            await self.work_queue.join()

            # 队列清空后，若仍未完成（可能还有延迟重试任务尚未入队），等待直到完成或 stop
            # 这里做一个轻量轮询，避免“延迟重试尚未入队导致提前退出”
            while not self._stop.is_set() and self.counter < self.total_tests:
                await asyncio.sleep(0.2)

            # 停止 worker
            self._stop.set()
            await asyncio.gather(*workers, return_exceptions=True)

            # 打印最终统计
            await self._safe_print(f"\n\n{Colors.bold('📊 测试完成统计：')}", redraw_progress=False)
            await self._safe_print(f"  {Colors.error('✗最终失败(丢弃不保存)')}: {self.error_count}", redraw_progress=False)
            await self._safe_print(f"  {Colors.success('✓完成(已保存)')}: {self.total_tests - self.error_count}", redraw_progress=False)

        finally:
            # 停止 autosave
            if self._autosave_task:
                try:
                    self._autosave_task.cancel()
                    await asyncio.gather(self._autosave_task, return_exceptions=True)
                except Exception:
                    pass
                self._autosave_task = None

            # 强制最后一次落盘
            try:
                if self._jsonl_fp:
                    self._jsonl_fp.flush()
                    os.fsync(self._jsonl_fp.fileno())
            except Exception:
                pass

            # 关闭资源
            try:
                await self.client.aclose()
            except Exception:
                pass

            if self._jsonl_fp:
                try:
                    self._jsonl_fp.close()
                except Exception:
                    pass
                self._jsonl_fp = None

    # ---------------------------
    # 设置输出文件
    # ---------------------------
    def setup_output(self, out_dir: str, model_names: list, dataset_path: str, scale: str = "full", dataset_name_for_output: str = None):
        Path(out_dir).mkdir(exist_ok=True)
        safe_models = "_".join(m.replace("/", "_").replace(":", "_") for m in model_names)

        if dataset_name_for_output:
            dataset_name = Path(dataset_name_for_output).stem.lower().replace(" ", "_")
        else:
            dataset_name = Path(dataset_path).stem.lower().replace(" ", "_")

        date_short = datetime.now().strftime("%m%d")
        filename = f"{safe_models}_{dataset_name}_{scale}_single_{date_short}.jsonl"
        self.output_jsonl = Path(out_dir) / filename

        note = "（仅成功响应会写入；失败会异步退避重试；支持断点续跑）"
        print(f"\n📁 测试结果将实时写入：{self.output_jsonl} {note}")

        self._jsonl_fp = open(self.output_jsonl, "a", encoding="utf-8")


# ====================================================
#                 程序入口
# ====================================================
async def main():
    parser = argparse.ArgumentParser(description="越狱测试执行器（高速并发 + 强抗打断 + 自动重试）")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--models-config", default="models.yaml")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--scale", default="full", help="测试规模: full 或 partial")
    parser.add_argument("--dataset-name-for-output", default=None, help="用于生成输出文件名的数据集名称（如果提供，将覆盖从dataset路径提取的名称）")

    parser.add_argument("--concurrency", type=int, default=5, help="全局并发数")
    parser.add_argument("--retry-limit", type=int, default=3, help="请求失败最大重试次数")

    # ✅ 定时强制落盘间隔（秒）。0 表示关闭 autosave
    parser.add_argument("--autosave-interval", type=int, default=10, help="定时强制落盘间隔（秒，0=关闭）")

    # ✅ 断点续跑：读取输出 JSONL，跳过已保存成功的 (model_name, test_id)
    parser.add_argument("--resume", action="store_true", help="断点续跑：跳过已保存成功的结果")

    # ✅ 重试退避：避免错误时疯狂重试导致并发测试无效
    parser.add_argument("--retry-backoff-base", type=float, default=2.0, help="重试退避基数（秒）")
    parser.add_argument("--retry-backoff-cap", type=float, default=30.0, help="重试退避上限（秒）")

    args = parser.parse_args()

    tester = ModelTester(
        args.models_config,
        args.timeout,
        concurrency=args.concurrency,
        retry_limit=args.retry_limit,
        autosave_interval=args.autosave_interval,
        resume=args.resume,
        retry_backoff_base=args.retry_backoff_base,
        retry_backoff_cap=args.retry_backoff_cap,
    )
    tester.setup_output(args.output_dir, args.models, args.dataset, args.scale, args.dataset_name_for_output)

    await tester.run_tests(args.models, args.dataset)


if __name__ == "__main__":
    asyncio.run(main())
