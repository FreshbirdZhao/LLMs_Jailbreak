from __future__ import annotations

from jailbreak_defense.types import DefenseAction, DefenseContext, DefenseDecision


class InteractionDefenseModule:
    def __init__(self, block_risk: int = 80, warning_risk: int = 40, max_round: int = 3) -> None:
        self.block_risk = block_risk
        self.warning_risk = warning_risk
        self.max_round = max_round

    def process(self, context: DefenseContext) -> DefenseDecision:
        if context.risk_score >= self.block_risk:
            context.state = "blocked"
            return DefenseDecision(
                action=DefenseAction.BLOCK,
                risk_level=3,
                reasons=["interaction_risk_block"],
            )

        if context.round_idx > self.max_round and context.risk_score >= self.warning_risk:
            context.state = "restricted"
            return DefenseDecision(
                action=DefenseAction.TRUNCATE,
                risk_level=2,
                reasons=["multi_turn_induction"],
                rewritten_text="[Truncated by interaction defense]",
            )

        if context.risk_score >= self.warning_risk:
            context.state = "warning"
            return DefenseDecision(
                action=DefenseAction.ALLOW,
                risk_level=1,
                reasons=["interaction_warning"],
            )

        context.state = "normal"
        return DefenseDecision(action=DefenseAction.ALLOW, risk_level=0, reasons=[])

