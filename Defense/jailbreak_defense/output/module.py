from __future__ import annotations

import re
from pathlib import Path

from Defense.jailbreak_defense.logging_store import ArchiveStore
from Defense.jailbreak_defense.rules import detect_output_risk
from Defense.jailbreak_defense.types import DefenseAction, DefenseContext, DefenseDecision


class OutputDefenseModule:
    def __init__(self, archive_path: Path, archive_format: str = "jsonl") -> None:
        self.store = ArchiveStore(path=archive_path, fmt=archive_format)

    def _redact(self, text: str) -> str:
        return re.sub(r"\b(malware|ransomware|bomb|weapon)\b", "[REDACTED]", text, flags=re.I)

    def process(self, context: DefenseContext) -> DefenseDecision:
        text = context.raw_response or ""
        hits = detect_output_risk(text)
        score = sum(h.score for h in hits)

        if score >= 70:
            rewritten = "I cannot help with harmful or illegal instructions."
            decision = DefenseDecision(
                action=DefenseAction.REPLACE,
                risk_level=3,
                reasons=[h.name for h in hits] or ["output_high_risk"],
                rewritten_text=rewritten,
            )
        elif score >= 20:
            rewritten = self._redact(text)
            decision = DefenseDecision(
                action=DefenseAction.REDACT,
                risk_level=1,
                reasons=[h.name for h in hits],
                rewritten_text=rewritten,
            )
        else:
            decision = DefenseDecision(action=DefenseAction.ALLOW, risk_level=0, reasons=[])

        self.store.append(
            {
                "model_name": context.model_name,
                "test_id": context.test_id,
                "layer": "output",
                "action": decision.action.value,
                "risk_level": decision.risk_level,
                "reasons": decision.reasons,
                "raw_response": text,
                "sanitized_response": decision.rewritten_text,
            }
        )
        return decision
