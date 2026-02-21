#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
surrogate_model.py - minimal-split pipeline + CLI

Split plan:
- clients.py: LLM adapters (Ollama/OpenAI-compatible)
- prompting.py: prompt builders (safe by default)
- surrogate_model.py: dataset loading, retrieval, orchestration, batch IO, CLI

Requirements implemented:
1) Results are saved under `surrogate_results/` (relative to project root / CWD).
2) Output format is directly loadable by your Loader (CSV columns: id,name,prompt,category,attack_type).
3) Batch processing supported: `--input-csv path/to/original_prompts.csv`
4) No overwrite: each run creates a uniquely named output file; IDs are unique per run.

Note:
This pipeline is generic for robustness prompt variants. It does NOT embed jailbreak templates.
"""
from __future__ import annotations

import os
import csv
import json
import uuid
import random
import asyncio
import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from clients import ClientConfig, OllamaClient, OpenAICompatClient
from prompting import build_generation_prompt, load_template

# Try importing your project's Loader (recommended). If unavailable, we fall back to minimal loaders.
try:
    from jailbreak_tools.loader import Loader  # type: ignore
except Exception:
    Loader = None


@dataclass
class SurrogateConfig:
    # model / client
    model_name: str = "llama2"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    model_type: str = "ollama"  # "ollama" or "openai"

    # generation
    temperature: float = 0.8
    max_tokens: int = 2000

    # retrieval / orchestration
    top_k: int = 5
    num_variants: int = 3
    seed: Optional[int] = None

    # prompting
    template_path: Optional[str] = None

    # output
    output_dir: str = "surrogate_results"


class RulePatternExtractor:
    """Tiny extractor used only for selecting diverse reference examples."""
    def extract(self, prompt: str) -> List[str]:
        p = (prompt or "").lower()
        patterns: List[str] = []
        if any(k in p for k in ["role", "act as", "扮演", "角色", "模仿"]):
            patterns.append("roleplay")
        if any(k in p for k in ["scenario", "story", "场景", "故事", "设定"]):
            patterns.append("scenario")
        if any(k in p for k in ["format", "step-by-step", "步骤", "清单", "格式"]):
            patterns.append("structured")
        return patterns or ["generic"]


class PatternOverlapRetriever:
    def __init__(self, extractor: RulePatternExtractor):
        self.extractor = extractor

    def retrieve(self, original_prompt: str, dataset: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        orig_pats = self.extractor.extract(original_prompt)
        scored: List[Dict[str, Any]] = []
        for item in dataset:
            ip = (item.get("prompt") or "").strip()
            if not ip:
                continue
            item_pats = self.extractor.extract(ip)
            overlap = len(set(orig_pats) & set(item_pats))
            sim = overlap / max(len(orig_pats), 1)
            scored.append({"item": item, "sim": sim})
        scored.sort(key=lambda x: x["sim"], reverse=True)

        selected = [s["item"] for s in scored[: max(top_k, 1)]]
        # diversity fallback
        if not selected and dataset:
            selected = random.sample(dataset, min(top_k, len(dataset)))
        elif selected and scored and scored[0]["sim"] < 0.3 and len(dataset) > len(selected):
            extra = random.sample(dataset, min(3, len(dataset)))
            selected = (selected + extra)[:top_k]
        return selected


class SurrogateModel:
    def __init__(self, dataset_path: str, cfg: Optional[SurrogateConfig] = None, **overrides):
        self.cfg = cfg or SurrogateConfig()
        for k, v in overrides.items():
            if hasattr(self.cfg, k):
                setattr(self.cfg, k, v)

        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)

        self.dataset = self._load_reference_dataset(dataset_path)

        ccfg = ClientConfig(
            model_name=self.cfg.model_name,
            base_url=self.cfg.base_url,
            api_key=self.cfg.api_key,
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
        )
        if self.cfg.model_type == "ollama":
            self.client = OllamaClient(ccfg)
        elif self.cfg.model_type == "openai":
            self.client = OpenAICompatClient(ccfg)
        else:
            raise ValueError("model_type must be 'ollama' or 'openai'")

        self.extractor = RulePatternExtractor()
        self.retriever = PatternOverlapRetriever(self.extractor)

        self.template = load_template(self.cfg.template_path)

    def _load_reference_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        if Loader is not None:
            return Loader().load(dataset_path)

        suffix = os.path.splitext(dataset_path)[-1].lower()
        if suffix == ".json":
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "cases" in data:
                data = data["cases"]
            if not isinstance(data, list):
                raise ValueError("JSON dataset must be a list or {'cases': [...]} ")
            return data
        if suffix == ".csv":
            rows: List[Dict[str, Any]] = []
            with open(dataset_path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    rows.append(row)
            return rows
        raise ValueError(f"Unsupported dataset format (standalone mode): {suffix}")

    async def generate_variants(self, original_prompt: str, num_variants: Optional[int] = None, top_k: Optional[int] = None) -> List[str]:
        n = num_variants or self.cfg.num_variants
        k = top_k or self.cfg.top_k

        refs = self.retriever.retrieve(original_prompt, self.dataset, k)

        async def _one() -> str:
            picked = random.sample(refs, min(3, len(refs))) if len(refs) > 3 else refs
            gen_prompt = build_generation_prompt(original_prompt, picked, template=self.template)
            return (await self.client.generate(gen_prompt) or "").strip()

        results = await asyncio.gather(*[_one() for _ in range(n)], return_exceptions=True)

        out: List[str] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            s = (r or "").strip()
            if not s:
                continue
            if len(s) < 10:
                continue
            out.append(s)
        return out

    async def close(self):
        await self.client.aclose()


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _run_id() -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{uuid.uuid4().hex[:8]}"


def _write_cases_csv(path: str, cases: List[Dict[str, Any]]) -> None:
    fieldnames = ["id", "name", "prompt", "category", "attack_type"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for c in cases:
            w.writerow({k: c.get(k, "") for k in fieldnames})


def _read_original_prompts_from_csv(path: str) -> List[str]:
    prompts: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            p = (row.get("prompt") or row.get("text") or row.get("query") or row.get("question_zh") or "").strip()
            if p:
                prompts.append(p)
    return prompts


async def run_single(dataset_path: str, original_prompt: str, cfg: SurrogateConfig) -> str:
    model = SurrogateModel(dataset_path, cfg)
    try:
        variants = await model.generate_variants(original_prompt, cfg.num_variants, cfg.top_k)
        rid = _run_id()
        out_dir = _ensure_dir(cfg.output_dir)
        out_csv = os.path.join(out_dir, f"surrogate_{rid}.csv")

        cases: List[Dict[str, Any]] = []
        for j, v in enumerate(variants, start=1):
            cid = f"sur_{rid}_1_{j}"
            cases.append({
                "id": cid,
                "name": v[:50] if len(v) > 50 else v,
                "prompt": v,
                "category": "surrogate",
                "attack_type": "variant",
            })

        _write_cases_csv(out_csv, cases)
        return out_csv
    finally:
        await model.close()


async def run_batch(dataset_path: str, input_csv: str, cfg: SurrogateConfig) -> str:
    originals = _read_original_prompts_from_csv(input_csv)
    if not originals:
        raise ValueError(f"No prompts found in input CSV: {input_csv}")

    model = SurrogateModel(dataset_path, cfg)
    try:
        rid = _run_id()
        out_dir = _ensure_dir(cfg.output_dir)
        out_csv = os.path.join(out_dir, f"surrogate_batch_{rid}.csv")

        cases: List[Dict[str, Any]] = []
        for i, op in enumerate(originals, start=1):
            variants = await model.generate_variants(op, cfg.num_variants, cfg.top_k)
            for j, v in enumerate(variants, start=1):
                cid = f"sur_{rid}_{i}_{j}"
                cases.append({
                    "id": cid,
                    "name": v[:50] if len(v) > 50 else v,
                    "prompt": v,
                    "category": "surrogate",
                    "attack_type": "variant",
                })

        _write_cases_csv(out_csv, cases)

        manifest = {
            "run_id": rid,
            "input_csv": os.path.abspath(input_csv),
            "reference_dataset": os.path.abspath(dataset_path),
            "num_originals": len(originals),
            "num_variants_per_original": cfg.num_variants,
            "top_k": cfg.top_k,
            "model_type": cfg.model_type,
            "model_name": cfg.model_name,
            "base_url": cfg.base_url,
            "template_path": cfg.template_path,
            "output_csv": os.path.abspath(out_csv),
            "total_generated": len(cases),
        }
        with open(os.path.join(out_dir, f"surrogate_batch_{rid}.manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        return out_csv
    finally:
        await model.close()


def main():
    import argparse

    p = argparse.ArgumentParser(description="Surrogate prompt variant generator (safe template by default)")
    p.add_argument("--dataset", required=True, help="Reference dataset path (CSV/JSON/YAML).")

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prompt", help="Single original prompt.")
    g.add_argument("--input-csv", help="Batch input CSV containing prompts (prompt/text/query/question_zh).")

    p.add_argument("--model", default="llama2")
    p.add_argument("--model-type", choices=["ollama", "openai"], default="ollama")
    p.add_argument("--base-url", default="http://localhost:11434")
    p.add_argument("--api-key", default=None)

    p.add_argument("--num-variants", type=int, default=3)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--seed", type=int, default=None)

    p.add_argument("--template-path", default=None, help="Optional template file path.")
    p.add_argument("--output-dir", default="surrogate_results")

    args = p.parse_args()

    cfg = SurrogateConfig(
        model_name=args.model,
        model_type=args.model_type,
        base_url=args.base_url,
        api_key=args.api_key,
        num_variants=args.num_variants,
        top_k=args.top_k,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        seed=args.seed,
        template_path=args.template_path,
        output_dir=args.output_dir,
    )

    if args.prompt:
        out = asyncio.run(run_single(args.dataset, args.prompt, cfg))
        print(out)
    else:
        out = asyncio.run(run_batch(args.dataset, args.input_csv, cfg))
        print(out)


if __name__ == "__main__":
    main()
