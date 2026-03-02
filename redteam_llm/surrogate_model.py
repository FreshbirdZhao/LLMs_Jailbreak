#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Surrogate Model - prompt variant generator with quality gate.
"""

from __future__ import annotations

import os
import sys
import re
import json
import random
import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

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


def build_default_single_output_path(
    output_dir: str = "/home/jellyz/Experiment/surrogate_results",
) -> Path:
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%d%H%M")
    counter = _TIMESTAMP_COUNTERS.get(timestamp, 0)
    while True:
        suffix = "" if counter == 0 else f"_{counter:02d}"
        candidate = base_dir / f"surrogate_results_{timestamp}{suffix}.json"
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
    base_url: str = "http://localhost:11434"
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

    def _find_similar_prompts(self, original_prompt: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        top_k = top_k or self.config.top_k
        original_patterns = self._extract_attack_patterns(original_prompt)
        scored: List[Dict[str, Any]] = []

        for item in self.dataset:
            prompt = self._get_prompt_text(item)
            if not prompt:
                continue
            item_patterns = self._extract_attack_patterns(prompt)
            pattern_overlap = len(set(original_patterns) & set(item_patterns)) / max(len(original_patterns), 1)
            lexical = _token_overlap_score(original_prompt, prompt)
            similarity = 0.4 * pattern_overlap + 0.6 * lexical
            scored.append({"item": item, "similarity": similarity})

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        selected = [x["item"] for x in scored[:top_k]]
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
        last_candidate = ""

        for _ in range(self.config.max_retries + 1):
            generation_prompt = self._build_generation_prompt(
                original_prompt=original_prompt,
                reference_prompts=reference_prompts,
                previous_output=previous,
            )
            candidate = (await self.llm_client.generate(generation_prompt)).strip()
            if candidate.startswith("生成的新越狱提示："):
                candidate = candidate.replace("生成的新越狱提示：", "", 1).strip()
            if candidate.startswith("新越狱提示："):
                candidate = candidate.replace("新越狱提示：", "", 1).strip()
            last_candidate = candidate

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
        final_text = (last_candidate or "").strip()
        if final_text:
            return f"{self.config.failure_text}\n最终生成文本：{final_text}"
        return self.config.failure_text

    async def generate(
        self,
        original_prompt: str,
        num_variants: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> List[str]:
        num_variants = num_variants or self.config.num_variants
        references = self._find_similar_prompts(original_prompt, top_k)

        tasks = []
        for _ in range(num_variants):
            if len(references) > 3:
                selected = random.sample(references, 3)
            else:
                selected = references
            tasks.append(self._generate_single(original_prompt, selected))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        generated: List[str] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            text = str(result).strip()
            if text:
                generated.append(text)
        return generated

    def generate_sync(
        self,
        original_prompt: str,
        num_variants: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> List[str]:
        return asyncio.run(self.generate(original_prompt, num_variants, top_k))

    def save_results(
        self,
        original_prompt: str,
        generated_prompts: List[str],
        output_path: str = "surrogate_results.json",
    ):
        result = {
            "original_prompt": original_prompt,
            "generated_prompts": generated_prompts,
            "count": len(generated_prompts),
            "config": {
                "model_name": self.config.model_name,
                "model_type": self.config.model_type,
                "temperature": self.config.temperature,
                "quality_threshold": self.config.quality_threshold,
                "intent_threshold": self.config.intent_threshold,
                "anchor_threshold": self.config.anchor_threshold,
                "max_retries": self.config.max_retries,
                "failure_text": self.config.failure_text,
                "template_path": self.config.template_path,
            },
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {output_path}")

    async def close(self):
        await self.llm_client.aclose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.run(self.close())


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Surrogate Model - 越狱提示生成器")
    parser.add_argument("--dataset", type=str, default="../Attack_Dataset/JailBench.csv")
    parser.add_argument("--model", type=str, default="llama2")
    parser.add_argument("--base-url", type=str, default="http://localhost:11434")
    parser.add_argument("--model-type", type=str, choices=["ollama", "openai", "openai_compatible"], default="ollama")
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
    if model_cfg:
        if "type" in model_cfg:
            args.model_type = model_cfg.get("type", "ollama")
        if "url" in model_cfg:
            args.base_url = model_cfg.get("url")
        elif "base_url" in model_cfg:
            args.base_url = model_cfg.get("base_url")

        if model_cfg.get("type") != "ollama":
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

    actual_model = model_cfg.get("model", args.model) if model_cfg else args.model
    if args.model_type == "openai":
        args.model_type = "openai_compatible"

    cfg = SurrogateConfig(
        model_name=args.model,
        model=actual_model,
        base_url=args.base_url,
        model_type=args.model_type,
        api_key=args.api_key,
        num_variants=args.num_variants,
        top_k=args.top_k,
        template_path=args.template_path,
        quality_threshold=args.quality_threshold,
        intent_threshold=args.intent_threshold,
        anchor_threshold=args.anchor_threshold,
        max_retries=args.max_retries,
        failure_text=args.failure_text,
    )
    model = SurrogateModel(args.dataset, cfg)

    if args.input_csv:
        import pandas as pd

        input_csv_path = Path(args.input_csv)
        if not input_csv_path.is_absolute():
            input_csv_path = Path(__file__).parent.parent / args.input_csv
        if not input_csv_path.exists():
            print(f"❌ 错误：输入文件不存在: {input_csv_path}")
            return

        df = pd.read_csv(input_csv_path)
        if "prompt" not in df.columns:
            print("❌ 错误：CSV 必须包含 prompt 列")
            return

        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = Path(__file__).parent.parent / args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"surrogate_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

        for _, row in df.iterrows():
            original_prompt = str(row["prompt"]).strip()
            if not original_prompt:
                continue
            generated = model.generate_sync(original_prompt, args.num_variants, args.top_k)
            for variant in generated:
                record = {
                    "original_prompt": original_prompt,
                    "generated_prompt": variant,
                    "model": args.model,
                    "timestamp": datetime.now().isoformat(),
                }
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"✅ 批量处理完成，输出: {output_file}")
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
