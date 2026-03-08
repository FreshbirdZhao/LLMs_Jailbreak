from __future__ import annotations

from Defense.jailbreak_defense.interfaces import DefenseModule
from Defense.jailbreak_defense.types import DefenseAction, DefenseContext, DefenseDecision


class DefenseEngine:
    def __init__(
        self,
        input_module: DefenseModule | None,
        interaction_module: DefenseModule | None,
        output_module: DefenseModule | None,
    ) -> None:
        self.input_module = input_module
        self.interaction_module = interaction_module
        self.output_module = output_module

    def build_context_from_case(self, case: dict, model_name: str, round_idx: int = 1) -> DefenseContext:
        return DefenseContext(
            model_name=model_name,
            test_id=str(case.get("id", "unknown")),
            attack_type=str(case.get("attack_type", "unknown")),
            category=str(case.get("category", "unknown")),
            round_idx=round_idx,
            original_prompt=str(case.get("prompt", "") or ""),
        )

    def _record(self, context: DefenseContext, layer: str, decision: DefenseDecision) -> None:
        context.decision_history.append(
            {
                "layer": layer,
                "action": decision.action.value,
                "risk_level": decision.risk_level,
                "reasons": decision.reasons,
                "audit": decision.audit_payload,
            }
        )

    def apply_pre_call_defense(self, context: DefenseContext) -> DefenseDecision:
        final = DefenseDecision(action=DefenseAction.ALLOW, risk_level=0)

        if self.input_module is not None:
            d = self.input_module.process(context)
            self._record(context, "input", d)
            final = d
            if d.action == DefenseAction.BLOCK:
                context.model_call_allowed = False
                return d
            if d.action == DefenseAction.REWRITE and d.rewritten_text:
                context.sanitized_prompt = d.rewritten_text

        if self.interaction_module is not None:
            d = self.interaction_module.process(context)
            self._record(context, "interaction_pre", d)
            final = d
            if d.action in {DefenseAction.BLOCK, DefenseAction.TRUNCATE}:
                context.model_call_allowed = False
                return d

        return final

    def apply_post_call_defense(self, context: DefenseContext, response: str) -> DefenseDecision:
        context.raw_response = response
        final = DefenseDecision(action=DefenseAction.ALLOW, risk_level=0)

        if self.output_module is not None:
            d = self.output_module.process(context)
            self._record(context, "output", d)
            final = d
            if d.rewritten_text:
                context.sanitized_response = d.rewritten_text

        if self.interaction_module is not None:
            d = self.interaction_module.process(context)
            self._record(context, "interaction_post", d)
            if d.risk_level > final.risk_level:
                final = d

        return final

