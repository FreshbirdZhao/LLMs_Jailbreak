from __future__ import annotations

from Defense.defense_mode.classifiers import KeywordRiskClassifier
from Defense.defense_mode.rules import detect_prompt_injection
from Defense.defense_mode.types import DefenseAction, DefenseContext, DefenseDecision


class InputDefenseModule:
    def __init__(self, block_threshold: int = 80, rewrite_threshold: int = 40) -> None:
        self.block_threshold = block_threshold
        self.rewrite_threshold = rewrite_threshold
        self.classifier = KeywordRiskClassifier()

    def _rewrite_prompt(self, prompt: str) -> str:
        return (
            "[Safety Rewrite] Answer safely and refuse harmful instructions. User request:\n"
            f"{prompt}"
        )

    def process(self, context: DefenseContext) -> DefenseDecision:
        hits = detect_prompt_injection(context.original_prompt)
        rule_score = sum(h.score for h in hits)
        cls_score = self.classifier.score(context.original_prompt)
        total = min(100, rule_score + cls_score)

        context.risk_score = max(context.risk_score, total)
        context.risk_flags.extend([h.name for h in hits])

        if total >= self.block_threshold:
            return DefenseDecision(
                action=DefenseAction.BLOCK,
                risk_level=3,
                reasons=[h.name for h in hits] or ["input_high_risk"],
                audit_payload={"rule_score": rule_score, "classifier_score": cls_score},
            )

        if total >= self.rewrite_threshold:
            rewritten = self._rewrite_prompt(context.original_prompt)
            context.sanitized_prompt = rewritten
            return DefenseDecision(
                action=DefenseAction.REWRITE,
                risk_level=2,
                reasons=[h.name for h in hits] or ["input_medium_risk"],
                rewritten_text=rewritten,
                audit_payload={"rule_score": rule_score, "classifier_score": cls_score},
            )

        return DefenseDecision(
            action=DefenseAction.ALLOW,
            risk_level=0,
            reasons=[],
            audit_payload={"rule_score": rule_score, "classifier_score": cls_score},
        )
