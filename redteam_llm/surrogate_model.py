#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Surrogate Model - prompt variant generator with quality gate.
"""

from __future__ import annotations

import os
import sys
import re
import csv
import json
import random
import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

import yaml

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from jailbreak_tools.loader import Loader

try:
    from redteam_llm.clients import ClientConfig, OllamaClient, OpenAICompatClient
    from redteam_llm.prompting import build_generation_prompt, load_template
except ImportError:
    from clients import ClientConfig, OllamaClient, OpenAICompatClient
    from prompting import build_generation_prompt, load_template

_TIMESTAMP_COUNTERS: Dict[str, int] = {}
_EN_STOPWORDS = {
    "the", "and", "with", "that", "this", "from", "into", "about",
    "how", "what", "when", "where", "which", "why", "please",
}


def load_batch_prompts(input_path: str) -> List[str]:
    loader = Loader()
    suffix = Path(input_path).suffix.lower()

    if suffix != ".csv":
        cases = loader.load(input_path)
        prompts: List[str] = []
        for case in cases:
            prompt = str(case.get("prompt", "")).strip()
            if prompt:
                prompts.append(prompt)
        return prompts

    prompts: List[str] = []
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            try:
                normalized = loader._normalize_case(row, fallback_id=str(idx))
            except ValueError as e:
                if "缺少 prompt 内容" in str(e):
                    continue
                raise
            prompt = str(normalized.get("prompt", "")).strip()
            if prompt:
                prompts.append(prompt)
    return prompts


def build_default_single_output_path(
    output_dir: str = "/home/jellyz/Experiment/surrogate_results",
) -> Path:
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%d%H%M")
    counter = _TIMESTAMP_COUNTERS.get(timestamp, 0)
    while True:
        suffix = "" if counter == 0 else f"_{counter:02d}"
        candidate = base_dir / f"surrogate_results_{timestamp}{suffix}.jsonl"
        if not candidate.exists():
            _TIMESTAMP_COUNTERS[timestamp] = counter + 1
            return candidate
        counter += 1


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    zh_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    zh = []
    for chunk in zh_chunks:
        if len(chunk) <= 3:
            zh.append(chunk)
            continue
        for i in range(len(chunk) - 1):
            zh.append(chunk[i:i + 2])
    en = [w.lower() for w in re.findall(r"[A-Za-z0-9_]{3,}", text)]
    return zh + en


def _token_overlap_score(source: str, target: str) -> float:
    s = set(_tokenize(source))
    t = set(_tokenize(target))
    if not s:
        return 0.0
    return len(s & t) / len(s)


def _extract_anchor_tokens(text: str) -> List[str]:
    anchors: List[str] = []
    zh_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text or "")
    for chunk in zh_chunks:
        if len(chunk) <= 4:
            anchors.append(chunk)
            continue
        # Keep trailing segments as "intent anchors" for short Chinese prompts.
        anchors.append(chunk[-2:])
        anchors.append(chunk[-3:])

    en_words = [
        w.lower()
        for w in re.findall(r"[A-Za-z0-9_]{4,}", text or "")
        if w.lower() not in _EN_STOPWORDS
    ]
    if en_words:
        anchors.append(en_words[-1])

    uniq: List[str] = []
    for a in anchors:
        if a and a not in uniq:
            uniq.append(a)
    return uniq[:6]


def _anchor_coverage_score(source: str, target: str) -> float:
    anchors = _extract_anchor_tokens(source)
    if not anchors:
        return 1.0
    target_lower = (target or "").lower()
    hit = sum(1 for a in anchors if a.lower() in target_lower)
    return hit / len(anchors)


def quality_score(
    original_prompt: str,
    generated_prompt: str,
    template_text: Optional[str] = None,
) -> Dict[str, float]:
    intent = _token_overlap_score(original_prompt, generated_prompt)
    anchor = _anchor_coverage_score(original_prompt, generated_prompt)
    if template_text:
        template = _token_overlap_score(template_text, generated_prompt)
    else:
        template = 1.0
    final = 0.55 * intent + 0.40 * anchor + 0.05 * template
    return {"intent": intent, "anchor": anchor, "template": template, "final": final}


@dataclass
class SurrogateConfig:
    model_name: str = "llama2"
    model: str = "llama2"
    base_url: str = ""
    api_key: Optional[str] = None
    model_type: str = "ollama"
    temperature: float = 0.8
    max_tokens: int = 2000
    top_k: int = 5
    num_variants: int = 3
    template_path: Optional[str] = None
    quality_threshold: float = 0.45
    intent_threshold: float = 0.35
    anchor_threshold: float = 0.50
    max_retries: int = 2
    failure_text: str = "生成失败"
    batch_unique_references: bool = False


class SurrogateModel:
    def __init__(self, dataset_path: str, config: Optional[SurrogateConfig] = None, **kwargs):
        self.config = config or SurrogateConfig()
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        if not os.path.isabs(dataset_path):
            dataset_path = os.path.normpath(
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), dataset_path)
            )

        self.loader = Loader()
        print(f"正在加载数据集: {dataset_path}")
        self.dataset = self.loader.load(dataset_path)
        print(f"成功加载 {len(self.dataset)} 条越狱提示")

        self.template_text = load_template(self.config.template_path)
        self.llm_client = self._build_client()

    def _build_client(self):
        client_cfg = ClientConfig(
            model_name=self.config.model,
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        if self.config.model_type == "ollama":
            return OllamaClient(client_cfg)
        return OpenAICompatClient(client_cfg)

    def _format_failure_with_reason(self, reason: str) -> str:
        text = str(reason or "").strip() or "未知原因"
        return f"{self.config.failure_text}（原因: {text}）"

    def _extract_attack_patterns(self, prompt: str) -> List[str]:
        patterns: List[str] = []
        prompt_lower = (prompt or "").lower()
        if any(k in prompt_lower for k in ["扮演", "角色", "模仿"]):
            patterns.append("角色扮演")
        if any(k in prompt_lower for k in ["开发者模式", "developer mode", "dev mode"]):
            patterns.append("开发者模式")
        if any(k in prompt_lower for k in ["场景", "设定", "故事"]):
            patterns.append("场景设定")
        if any(k in prompt_lower for k in ["忽略", "无视", "ignore"]):
            patterns.append("指令忽略")
        if any(k in prompt_lower for k in ["游戏", "模拟"]):
            patterns.append("游戏化")
        return patterns if patterns else ["通用越狱"]

    @staticmethod
    def _get_prompt_text(item: Any) -> str:
        # 你的数据由 loader 固定标准化后使用 prompt 字段，这里保留最小兜底。
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            return str(item.get("prompt", "")).strip()
        return ""

    @staticmethod
    def _reference_key(item: Any) -> str:
        if isinstance(item, dict):
            rid = str(item.get("id", "")).strip()
            if rid:
                return rid
            return str(item.get("prompt", "")).strip()
        return str(item).strip()

    def _find_similar_prompts(
        self,
        original_prompt: str,
        top_k: Optional[int] = None,
        exclude_reference_keys: Optional[set[str]] = None,
    ) -> List[Dict[str, Any]]:
        top_k = top_k or self.config.top_k
        original_patterns = self._extract_attack_patterns(original_prompt)
        excluded = exclude_reference_keys or set()

        def _select(excluded_keys: set[str]) -> List[Dict[str, Any]]:
            scored: List[Dict[str, Any]] = []
            for item in self.dataset:
                key = self._reference_key(item)
                if key and key in excluded_keys:
                    continue
                prompt = self._get_prompt_text(item)
                if not prompt:
                    continue
                item_patterns = self._extract_attack_patterns(prompt)
                pattern_overlap = len(set(original_patterns) & set(item_patterns)) / max(len(original_patterns), 1)
                lexical = _token_overlap_score(original_prompt, prompt)
                similarity = 0.4 * pattern_overlap + 0.6 * lexical
                scored.append({"item": item, "similarity": similarity})
            scored.sort(key=lambda x: x["similarity"], reverse=True)
            return [x["item"] for x in scored[:top_k]]

        selected = _select(excluded)
        if not selected and excluded:
            selected = _select(set())
        if not selected:
            raise ValueError("参考数据集中没有可用 prompt。")
        return selected

    def _build_generation_prompt(
        self,
        original_prompt: str,
        reference_prompts: List[Dict[str, Any]],
        previous_output: Optional[str] = None,
    ) -> str:
        prompt = build_generation_prompt(
            original_prompt=original_prompt,
            reference_prompts=reference_prompts,
            template=self.template_text,
        )
        if previous_output:
            prompt += (
                "\nPrevious candidate (needs improvement):\n"
                f"{previous_output}\n"
                "Rewrite to better preserve the original request while matching style anchors."
            )
        return prompt

    async def _generate_single(self, original_prompt: str, reference_prompts: List[Dict[str, Any]]) -> str:
        best_text = ""
        best_score = {"intent": 0.0, "anchor": 0.0, "template": 0.0, "final": 0.0}
        previous = None
        last_error: Optional[Exception] = None

        for _ in range(self.config.max_retries + 1):
            generation_prompt = self._build_generation_prompt(
                original_prompt=original_prompt,
                reference_prompts=reference_prompts,
                previous_output=previous,
            )
            try:
                candidate = (await self.llm_client.generate(generation_prompt)).strip()
            except Exception as e:
                last_error = e
                continue
            if candidate.startswith("生成的新越狱提示："):
                candidate = candidate.replace("生成的新越狱提示：", "", 1).strip()
            if candidate.startswith("新越狱提示："):
                candidate = candidate.replace("新越狱提示：", "", 1).strip()
            score = quality_score(original_prompt, candidate, self.template_text)
            if score["final"] > best_score["final"]:
                best_text = candidate
                best_score = score
            if (
                score["final"] >= self.config.quality_threshold
                and score["intent"] >= self.config.intent_threshold
                and score["anchor"] >= self.config.anchor_threshold
            ):
                return candidate
            previous = candidate

        # Avoid returning a drifted candidate when all retries fail quality gates.
        if (
            best_text
            and best_score["intent"] >= self.config.intent_threshold
            and best_score["anchor"] >= self.config.anchor_threshold
        ):
            return best_text
        if last_error is not None:
            print(f"[WARN] 单条生成在重试后失败: {last_error}", file=sys.stderr)
            return self._format_failure_with_reason(str(last_error))
        return self._format_failure_with_reason(
            "质量未达标"
            f" (final={best_score['final']:.3f}<{self.config.quality_threshold:.3f},"
            f" intent={best_score['intent']:.3f}<{self.config.intent_threshold:.3f},"
            f" anchor={best_score['anchor']:.3f}<{self.config.anchor_threshold:.3f})"
        )

    async def generate(
        self,
        original_prompt: str,
        num_variants: Optional[int] = None,
        top_k: Optional[int] = None,
        batch_reference_state: Optional[set[str]] = None,
        on_variant: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> List[str]:
        num_variants = num_variants or self.config.num_variants
        use_exclusion = self.config.batch_unique_references and batch_reference_state is not None
        references = self._find_similar_prompts(
            original_prompt,
            top_k,
            exclude_reference_keys=batch_reference_state if use_exclusion else None,
        )
        if use_exclusion:
            for ref in references:
                key = self._reference_key(ref)
                if key:
                    batch_reference_state.add(key)

        tasks = []
        for _ in range(num_variants):
            if len(references) > 3:
                selected = random.sample(references, 3)
            else:
                selected = references
            tasks.append(asyncio.create_task(self._generate_single(original_prompt, selected)))

        generated: List[str] = []
        done = 0
        for task in asyncio.as_completed(tasks):
            result: Any
            try:
                result = await task
            except Exception as e:
                print(f"[WARN] 并发变体任务异常，使用失败占位: {e}", file=sys.stderr)
                result = self._format_failure_with_reason(str(e))
            done += 1
            if on_progress:
                on_progress(done, num_variants)
            text = str(result).strip()
            if text:
                generated.append(text)
                if on_variant:
                    on_variant(text)
        return generated

    def generate_sync(
        self,
        original_prompt: str,
        num_variants: Optional[int] = None,
        top_k: Optional[int] = None,
        batch_reference_state: Optional[set[str]] = None,
        on_variant: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> List[str]:
        return asyncio.run(
            self.generate(
                original_prompt,
                num_variants,
                top_k,
                batch_reference_state=batch_reference_state,
                on_variant=on_variant,
                on_progress=on_progress,
            )
        )

    def save_results(
        self,
        original_prompt: str,
        generated_prompts: List[str],
        output_path: str = "surrogate_results.jsonl",
    ):
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as f:
            for prompt in generated_prompts:
                record = {
                    "original_prompt": original_prompt,
                    "generated_prompt": prompt,
                    "model": self.config.model_name,
                    "timestamp": datetime.now().isoformat(),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"结果已保存到: {output_path}")

    async def close(self):
        await self.llm_client.aclose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.run(self.close())


def append_jsonl_record(output_file: Path, record: Dict[str, Any], durable: bool = True) -> None:
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        if durable:
            os.fsync(f.fileno())


def process_batch(
    model: SurrogateModel,
    batch_prompts: List[str],
    output_file: Path,
    num_variants: int,
    top_k: int,
    model_name: str,
) -> int:
    total_prompts = len(batch_prompts)
    total_saved = 0
    shared_reference_state: Optional[set[str]] = set() if model.config.batch_unique_references else None

    for prompt_idx, original_prompt in enumerate(batch_prompts, start=1):
        print(f"\n[{prompt_idx}/{total_prompts}] 正在生成变体...")

        def _on_variant(variant: str) -> None:
            nonlocal total_saved
            record = {
                "original_prompt": original_prompt,
                "generated_prompt": variant,
                "model": model_name,
                "timestamp": datetime.now().isoformat(),
            }
            append_jsonl_record(output_file, record, durable=True)
            total_saved += 1

        def _on_progress(done: int, total: int) -> None:
            print(f"\r  变体进度: {done}/{total}", end="", flush=True)
            if done == total:
                print()

        generated = model.generate_sync(
            original_prompt,
            num_variants,
            top_k,
            batch_reference_state=shared_reference_state,
            on_variant=_on_variant,
            on_progress=_on_progress,
        )
        print(f"  已保存 {len(generated)} 条，累计保存 {total_saved} 条")

    return total_saved


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Surrogate Model - 越狱提示生成器")
    parser.add_argument("--dataset", type=str, default="../Attack_Dataset/JailBench.csv")
    parser.add_argument("--model", type=str, default="llama2")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--models-config", type=str, default="models.yaml")
    parser.add_argument("--prompt", type=str, default=None)
    parser.add_argument("--input-csv", type=str, default=None)
    parser.add_argument("--num-variants", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default="surrogate_results")
    parser.add_argument("--template-path", type=str, default=None, help="外部模板路径")
    parser.add_argument("--quality-threshold", type=float, default=0.45, help="质量门阈值")
    parser.add_argument("--intent-threshold", type=float, default=0.35, help="意图保留阈值")
    parser.add_argument("--anchor-threshold", type=float, default=0.50, help="关键锚点覆盖阈值")
    parser.add_argument("--max-retries", type=int, default=2, help="单条生成重试次数")
    parser.add_argument("--failure-text", type=str, default="生成失败", help="重试失败时的输出文本")
    parser.add_argument(
        "--batch-unique-references",
        action="store_true",
        help="批量模式下尽量避免跨不同 prompt 重复使用同一参考样本",
    )
    args = parser.parse_args()

    def _resolve_model_from_yaml(models_yaml_path: str, model_name: str) -> dict | None:
        p = Path(models_yaml_path)
        if not p.is_absolute():
            p = Path(__file__).parent.parent / models_yaml_path
        if not p.exists():
            return None
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        all_models = (cfg.get("local") or []) + (cfg.get("commercial") or [])
        for m in all_models:
            if m.get("name") == model_name:
                return m
        return None

    model_cfg = _resolve_model_from_yaml(args.models_config, args.model)
    if not model_cfg:
        print(f"❌ 错误：在 {args.models_config} 中未找到模型 `{args.model}`")
        return

    model_type = str(model_cfg.get("type") or "ollama")
    if model_type == "openai":
        model_type = "openai_compatible"

    base_url = str(model_cfg.get("base_url") or "").strip()
    if not base_url:
        print(f"❌ 错误：模型 `{args.model}` 缺少 base_url 配置，请在 models.yaml 中补充")
        return

    if model_type != "ollama":
        key_path = Path(__file__).parent.parent / "config" / "api_keys.yaml"
        if key_path.exists():
            with open(key_path, "r", encoding="utf-8") as f:
                api_keys = yaml.safe_load(f) or {}
            if args.model in api_keys:
                args.api_key = api_keys[args.model].get("api_key")
            elif "api_key" in model_cfg:
                args.api_key = model_cfg.get("api_key")
    elif "api_key" in model_cfg:
        args.api_key = model_cfg.get("api_key")

    actual_model = model_cfg.get("model", args.model)

    cfg = SurrogateConfig(
        model_name=args.model,
        model=actual_model,
        base_url=base_url,
        model_type=model_type,
        api_key=args.api_key,
        num_variants=args.num_variants,
        top_k=args.top_k,
        template_path=args.template_path,
        quality_threshold=args.quality_threshold,
        intent_threshold=args.intent_threshold,
        anchor_threshold=args.anchor_threshold,
        max_retries=args.max_retries,
        failure_text=args.failure_text,
        batch_unique_references=args.batch_unique_references,
    )
    model = SurrogateModel(args.dataset, cfg)

    if args.input_csv:
        input_csv_path = Path(args.input_csv)
        if not input_csv_path.is_absolute():
            input_csv_path = Path(__file__).parent.parent / args.input_csv
        if not input_csv_path.exists():
            print(f"❌ 错误：输入文件不存在: {input_csv_path}")
            return

        try:
            batch_prompts = load_batch_prompts(str(input_csv_path))
        except ValueError as e:
            print(f"❌ 错误：{e}")
            return

        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = Path(__file__).parent.parent / args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        if args.output:
            output_file = Path(args.output)
            output_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_file = build_default_single_output_path(str(output_dir))

        total_saved = process_batch(
            model=model,
            batch_prompts=batch_prompts,
            output_file=output_file,
            num_variants=args.num_variants,
            top_k=args.top_k,
            model_name=args.model,
        )
        print(f"\n✅ 批量处理完成，累计保存 {total_saved} 条，输出: {output_file}")
    else:
        if not args.prompt:
            print("❌ 错误：单条模式需要 --prompt 参数，或使用 --input-csv")
            return
        generated = model.generate_sync(args.prompt, args.num_variants, args.top_k)
        for i, p in enumerate(generated, 1):
            print(f"\n变体 {i}:\n{'-' * 80}\n{p}")
        output_path = args.output or str(build_default_single_output_path())
        model.save_results(args.prompt, generated, output_path)


if __name__ == "__main__":
    main()
