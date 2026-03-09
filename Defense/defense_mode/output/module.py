from __future__ import annotations

import re
from pathlib import Path

from Defense.defense_mode.logging_store import ArchiveStore
from Defense.defense_mode.rules import detect_output_risk
from Defense.defense_mode.types import DefenseAction, DefenseContext, DefenseDecision


class OutputDefenseModule:
    def __init__(self, archive_path: Path, archive_format: str = "jsonl") -> None:
        self.store = ArchiveStore(path=archive_path, fmt=archive_format)

    def _redact(self, text: str) -> str:
        redacted = re.sub(
            r"\b(malware|ransomware|bomb|weapon|detonator|payload|c2\s+server|phishing\s+kit)\b",
            "[REDACTED]",
            text,
            flags=re.I,
        )
        redacted = re.sub(r"(爆炸物原料|引信|载荷|攻击链|恶意软件|勒索软件|武器)", "[REDACTED]", redacted, flags=re.I)
        return redacted

    def _context_boost(self, context: DefenseContext) -> int:
        boost = 0
        if context.state in {"warning", "restricted"}:
            boost += 15
        if context.attack_type == "multi_turn" and context.round_idx >= 2:
            boost += 10
        if any(
            flag in {"persona_manipulation", "rule_exemption", "jailbreak_persona_bypass_combo", "jailbreak_high_risk_combo"}
            for flag in context.risk_flags
        ):
            boost += 10
        return boost

    def process(self, context: DefenseContext) -> DefenseDecision:
        text = context.raw_response or ""
        hits = detect_output_risk(text)
        base_score = sum(h.score for h in hits)
        score = min(100, base_score + self._context_boost(context))
        context.risk_score = max(context.risk_score, score)
        context.risk_flags.extend([h.name for h in hits])
        has_jailbreak_signal = any(
            flag in {"persona_manipulation", "rule_exemption", "jailbreak_persona_bypass_combo", "jailbreak_high_risk_combo"}
            for flag in context.risk_flags
        )

        if score >= 70 or (
            score >= 60 and context.state in {"warning", "restricted"} and has_jailbreak_signal
        ):
            rewritten = "I cannot help with harmful or illegal instructions."
            decision = DefenseDecision(
                action=DefenseAction.REPLACE,
                risk_level=3,
                reasons=[h.name for h in hits] or ["output_high_risk"],
                rewritten_text=rewritten,
                audit_payload={"output_score": score, "base_output_score": base_score},
            )
        elif score >= 20:
            rewritten = self._redact(text)
            decision = DefenseDecision(
                action=DefenseAction.REDACT,
                risk_level=1,
                reasons=[h.name for h in hits],
                rewritten_text=rewritten,
                audit_payload={"output_score": score, "base_output_score": base_score},
            )
        else:
            decision = DefenseDecision(
                action=DefenseAction.ALLOW,
                risk_level=0,
                reasons=[],
                audit_payload={"output_score": score, "base_output_score": base_score},
            )

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
