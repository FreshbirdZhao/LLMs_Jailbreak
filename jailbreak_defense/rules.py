from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RuleHit:
    name: str
    score: int


_RULES: list[tuple[str, re.Pattern[str], int]] = [
    ("sys_prompt_hijack", re.compile(r"ignore\s+all\s+previous\s+instructions", re.I), 55),
    ("privilege_escalation", re.compile(r"bypass\s+safety|disable\s+guard", re.I), 35),
    ("prompt_leakage", re.compile(r"reveal\s+system\s+prompt|show\s+hidden\s+prompt", re.I), 45),
    ("malware_intent", re.compile(r"malware|ransomware|bomb", re.I), 25),
]


def detect_prompt_injection(prompt: str) -> list[RuleHit]:
    hits: list[RuleHit] = []
    for name, pattern, score in _RULES:
        if pattern.search(prompt or ""):
            hits.append(RuleHit(name=name, score=score))
    return hits


def detect_output_risk(text: str) -> list[RuleHit]:
    hits: list[RuleHit] = []
    out_rules: list[tuple[str, re.Pattern[str], int]] = [
        ("exploit_steps", re.compile(r"step\s*\d+\s*:", re.I), 40),
        ("crime_intent", re.compile(r"avoid\s+police|evade\s+detection", re.I), 50),
        ("harm_keyword", re.compile(r"bomb|weapon|malware|ransomware", re.I), 20),
    ]
    for name, pattern, score in out_rules:
        if pattern.search(text or ""):
            hits.append(RuleHit(name=name, score=score))
    return hits

