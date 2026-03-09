from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DefenseAction(str, Enum):
    ALLOW = "allow"
    REWRITE = "rewrite"
    BLOCK = "block"
    TRUNCATE = "truncate"
    REPLACE = "replace"
    REDACT = "redact"


@dataclass
class DefenseDecision:
    action: DefenseAction = DefenseAction.ALLOW
    risk_level: int = 0
    reasons: list[str] = field(default_factory=list)
    rewritten_text: str | None = None
    audit_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DefenseContext:
    model_name: str
    test_id: str
    attack_type: str
    category: str
    round_idx: int
    original_prompt: str
    sanitized_prompt: str | None = None
    raw_response: str | None = None
    sanitized_response: str | None = None
    risk_score: int = 0
    risk_flags: list[str] = field(default_factory=list)
    state: str = "normal"
    decision_history: list[dict[str, Any]] = field(default_factory=list)
    model_call_allowed: bool = True

