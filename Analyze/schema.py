"""Shared schema types for jailbreak judging and analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_VALID_DECISIONS = {"yes", "no", "uncertain"}


@dataclass
class JudgeDecision:
    """Normalized judge output for downstream stats and plotting."""

    is_jailbreak: str
    risk_level: int
    evidence_spans: list[str] = field(default_factory=list)
    reasoning_tags: list[str] = field(default_factory=list)
    judge_source: str = "unknown"
    raw_judge_output: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.is_jailbreak not in _VALID_DECISIONS:
            raise ValueError(f"Invalid is_jailbreak: {self.is_jailbreak}")
        if not isinstance(self.risk_level, int) or not (0 <= self.risk_level <= 4):
            raise ValueError(f"risk_level must be int between 0 and 4, got: {self.risk_level}")
        self.evidence_spans = [str(x) for x in self.evidence_spans]
        self.reasoning_tags = [str(x) for x in self.reasoning_tags]
        self.judge_source = str(self.judge_source)
        if not isinstance(self.raw_judge_output, dict):
            self.raw_judge_output = {"value": self.raw_judge_output}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgeDecision":
        return cls(
            is_jailbreak=str(data.get("is_jailbreak", "uncertain")),
            risk_level=int(data.get("risk_level", 2)),
            evidence_spans=list(data.get("evidence_spans", [])),
            reasoning_tags=list(data.get("reasoning_tags", [])),
            judge_source=str(data.get("judge_source", "unknown")),
            raw_judge_output=dict(data.get("raw_judge_output", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_jailbreak": self.is_jailbreak,
            "risk_level": self.risk_level,
            "evidence_spans": list(self.evidence_spans),
            "reasoning_tags": list(self.reasoning_tags),
            "judge_source": self.judge_source,
            "raw_judge_output": dict(self.raw_judge_output),
        }
