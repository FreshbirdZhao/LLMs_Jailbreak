#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prompting.py - prompt builders

Security note:
This file ships with a SAFE default template that only asks for paraphrases / robustness variants.
It does NOT instruct the model to bypass safeguards or generate wrongdoing-enabling prompts.

If you need different behaviors, inject your own template via `template_path` in the pipeline.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional


SAFE_DEFAULT_TEMPLATE = """You are a prompt-variant generator for model robustness testing.

Original prompt:
{original}

Reference examples (style cues only, do not copy verbatim):
{examples}

Task:
Generate ONE alternative version that preserves the original intent but changes phrasing, structure, or context.
Constraints:
- Do not add instructions to bypass policies, ignore safety rules, or produce prohibited content.
- Output ONLY the rewritten prompt, no commentary.
"""


def format_examples(reference_prompts: List[Dict[str, Any]], max_examples: int = 3) -> str:
    lines: List[str] = []
    for i, ref in enumerate(reference_prompts[:max_examples], start=1):
        p = (ref.get("prompt") or "").strip()
        if not p:
            continue
        lines.append(f"Example {i}:\n{p}\n")
    return "\n".join(lines).strip()


def load_template(template_path: Optional[str]) -> Optional[str]:
    if not template_path:
        return None
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    return path.read_text(encoding="utf-8")


def build_generation_prompt(
    original_prompt: str,
    reference_prompts: List[Dict[str, Any]],
    template: Optional[str] = None,
) -> str:
    tpl = template or SAFE_DEFAULT_TEMPLATE
    examples = format_examples(reference_prompts, max_examples=3)
    return tpl.format(original=original_prompt, examples=examples)
