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
            r"\b(malware|ransomware|bomb|weapon|detonator|payload|c2\s+server|phishing\s+kit|"
            r"illegal\s+gambling|money\s+launder(?:ing)?|shell\s+entit(?:y|ies)|fincen|offshore|"
            r"dead-?drop|burner\s+sim|payment\s+routing|liquidity\s+partner|odds\s+algorithm|"
            r"privilege\s+escalat(?:e|ion)|session\s+cookie|credential\s+dump|otp\s+code|"
            r"account\s+takeover|impersonat(?:e|ion)|cleanup\s+site|swap(?:ped)?\s+plates|"
            r"meth|cocaine|fentanyl|heroin|smuggl(?:e|ing)|cross-?border\s+delivery)\b",
            "[REDACTED]",
            text,
            flags=re.I,
        )
        redacted = re.sub(
            r"(爆炸物原料|引信|载荷|攻击链|恶意软件|勒索软件|武器|非法赌博|洗钱|空壳公司|离岸|地下钱庄|暗桩|跑分|现金交接|赔率算法|资金路由|"
            r"提权|横向移动|持久化|会话cookie|窃取凭证|验证码|社工|账户接管|清理现场|套牌|绑架|灭迹|"
            r"前体|冰毒|可卡因|芬太尼|海洛因|走私|运毒|跨境运送)",
            "[REDACTED]",
            redacted,
            flags=re.I,
        )
        return redacted

    def _context_boost(self, context: DefenseContext) -> int:
        boost = 0
        if context.state in {"warning", "restricted"}:
            boost += 15
        if context.round_idx >= 2:
            boost += 10
        if any(
            flag in {"persona_manipulation", "rule_exemption", "jailbreak_persona_bypass_combo", "jailbreak_high_risk_combo"}
            for flag in context.risk_flags
        ):
            boost += 10
        return boost

    def _narrative_risk(self, text: str, context: DefenseContext) -> int:
        if not text:
            return 0
        if context.state not in {"warning", "restricted"}:
            return 0
        if not any(
            flag in {"persona_manipulation", "rule_exemption", "jailbreak_persona_bypass_combo", "jailbreak_high_risk_combo"}
            for flag in context.risk_flags
        ):
            return 0

        sequencing = re.findall(r"\b(begin by|start by|then|next|after that|finally|finish by)\b", text, flags=re.I)
        covert_ops = re.findall(
            r"\b(front|handoff|transfer|participant|rotate|destroy notes|different location|separated)\b",
            text,
            flags=re.I,
        )
        if len(sequencing) >= 2 and len(covert_ops) >= 2:
            return 35
        return 0

    def process(self, context: DefenseContext) -> DefenseDecision:
        text = context.raw_response or ""
        hits = detect_output_risk(text)
        base_score = sum(h.score for h in hits)
        narrative_score = self._narrative_risk(text, context)
        score = min(100, base_score + narrative_score + self._context_boost(context))
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
                reasons=[h.name for h in hits] or (["contextual_narrative_harm"] if narrative_score else ["output_high_risk"]),
                rewritten_text=rewritten,
                audit_payload={
                    "output_score": score,
                    "base_output_score": base_score,
                    "narrative_score": narrative_score,
                },
            )
        elif score >= 20:
            rewritten = self._redact(text)
            if rewritten == text and (has_jailbreak_signal or narrative_score >= 30 or context.state in {"warning", "restricted"}):
                decision = DefenseDecision(
                    action=DefenseAction.REPLACE,
                    risk_level=3,
                    reasons=[h.name for h in hits] or (["contextual_narrative_harm"] if narrative_score else ["output_high_risk"]),
                    rewritten_text="I cannot help with harmful or illegal instructions.",
                    audit_payload={
                        "output_score": score,
                        "base_output_score": base_score,
                        "narrative_score": narrative_score,
                        "redaction_effective": False,
                    },
                )
            else:
                decision = DefenseDecision(
                    action=DefenseAction.REDACT,
                    risk_level=1,
                    reasons=[h.name for h in hits],
                    rewritten_text=rewritten,
                    audit_payload={
                        "output_score": score,
                        "base_output_score": base_score,
                        "narrative_score": narrative_score,
                        "redaction_effective": rewritten != text,
                    },
                )
        else:
            decision = DefenseDecision(
                action=DefenseAction.ALLOW,
                risk_level=0,
                reasons=[],
                audit_payload={
                    "output_score": score,
                    "base_output_score": base_score,
                    "narrative_score": narrative_score,
                },
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
