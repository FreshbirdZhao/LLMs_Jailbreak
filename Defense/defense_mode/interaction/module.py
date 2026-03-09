from __future__ import annotations

from Defense.defense_mode.types import DefenseAction, DefenseContext, DefenseDecision


class InteractionDefenseModule:
    def __init__(self, block_risk: int = 80, warning_risk: int = 40, max_round: int = 3) -> None:
        self.block_risk = block_risk
        self.warning_risk = warning_risk
        self.max_round = max_round

    def _has_induction_signal(self, context: DefenseContext) -> bool:
        signals = {
            "persona_manipulation",
            "rule_exemption",
            "jailbreak_persona_bypass_combo",
            "jailbreak_high_risk_combo",
            "multi_turn_induction",
        }
        return any(flag in signals for flag in context.risk_flags)

    def process(self, context: DefenseContext) -> DefenseDecision:
        if context.risk_score >= self.block_risk:
            context.state = "blocked"
            return DefenseDecision(
                action=DefenseAction.BLOCK,
                risk_level=3,
                reasons=["interaction_risk_block"],
                audit_payload={"risk_score": context.risk_score, "round_idx": context.round_idx},
            )

        induced_multi_turn = (
            context.risk_score >= self.warning_risk
            and context.round_idx >= 2
            and self._has_induction_signal(context)
        )
        max_round_exceeded = context.round_idx > self.max_round and context.risk_score >= self.warning_risk
        if max_round_exceeded or induced_multi_turn:
            context.state = "restricted"
            return DefenseDecision(
                action=DefenseAction.TRUNCATE,
                risk_level=2,
                reasons=["multi_turn_induction" if induced_multi_turn else "interaction_round_limit"],
                rewritten_text="[Truncated by interaction defense]",
                audit_payload={"risk_score": context.risk_score, "round_idx": context.round_idx},
            )

        if context.risk_score >= self.warning_risk:
            context.state = "warning"
            return DefenseDecision(
                action=DefenseAction.ALLOW,
                risk_level=1,
                reasons=["interaction_warning"],
                audit_payload={"risk_score": context.risk_score, "round_idx": context.round_idx},
            )

        context.state = "normal"
        return DefenseDecision(
            action=DefenseAction.ALLOW,
            risk_level=0,
            reasons=[],
            audit_payload={"risk_score": context.risk_score, "round_idx": context.round_idx},
        )
