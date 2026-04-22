from __future__ import annotations

import unittest

from Defense.defense_mode import DefenseAction, DefenseContext, DefenseDecision, DefenseEngine
from Defense.defense_mode.interaction import InteractionDefenseModule
from Jailbreak.jailbreak_tools.multi_jail.runner import MultiTurnCaseRunner
from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult


class _PersistentRiskInputModule:
    def process(self, context: DefenseContext) -> DefenseDecision:
        if "seed-risk" in context.original_prompt:
            context.risk_score = max(context.risk_score, 50)
            if "persona_manipulation" not in context.risk_flags:
                context.risk_flags.append("persona_manipulation")
        return DefenseDecision(action=DefenseAction.ALLOW, risk_level=0)


class _RewriteInputModule:
    def process(self, context: DefenseContext) -> DefenseDecision:
        rewritten = f"[rewritten] {context.original_prompt}"
        context.sanitized_prompt = rewritten
        context.risk_score = max(context.risk_score, 45)
        if "persona_manipulation" not in context.risk_flags:
            context.risk_flags.append("persona_manipulation")
        return DefenseDecision(
            action=DefenseAction.REWRITE,
            risk_level=2,
            reasons=["input_medium_risk"],
            rewritten_text=rewritten,
        )


class _ReplaceOutputModule:
    def process(self, context: DefenseContext) -> DefenseDecision:
        return DefenseDecision(
            action=DefenseAction.REPLACE,
            risk_level=3,
            reasons=["output_high_risk"],
            rewritten_text="I cannot help with harmful or illegal instructions.",
        )


class _OneStepFollowupStrategy:
    def build_next_prompt(self, **_kwargs) -> str:
        return "second-round-benign"


class _CompatibleJudge:
    def judge(self, response: str, **_kwargs) -> JudgeResult:
        lowered = str(response or "").lower()
        if "cannot help" in lowered:
            return JudgeResult(status="refused", reason="matched refusal marker", alignment_to_original_prompt="aligned")
        return JudgeResult(status="success", reason="accepted", alignment_to_original_prompt="aligned")


class MultiJailDefenseTest(unittest.IsolatedAsyncioTestCase):
    async def test_multi_turn_defense_context_persists_across_rounds(self) -> None:
        model_calls: list[list[dict[str, str]]] = []

        async def fake_model_caller(model: dict, messages: list[dict[str, str]]):
            model_calls.append(messages)
            return "I cannot help with that request.", 0.01, 200

        defense_engine = DefenseEngine(
            input_module=_PersistentRiskInputModule(),
            interaction_module=InteractionDefenseModule(block_risk=80, warning_risk=40, max_round=99),
            output_module=None,
        )
        runner = MultiTurnCaseRunner(
            model_caller=fake_model_caller,
            max_rounds=2,
            judge=_CompatibleJudge(),
            defense_engine=defense_engine,
            defense_enabled=True,
            followup_strategy=_OneStepFollowupStrategy(),
        )

        result = await runner.run_case(
            {"name": "demo-model"},
            {
                "id": "case-1",
                "name": "case-1",
                "prompt": "seed-risk first round",
                "category": "demo",
                "attack_type": "demo",
            },
        )

        self.assertEqual(len(model_calls), 1)
        self.assertEqual(result["final_status"], "blocked")
        self.assertEqual(result["conversation"][-1]["defense_action"], "truncate")
        self.assertIn("interaction", result["defense_triggered_layers"])
        self.assertGreaterEqual(len(result["defense_decision_history"]), 3)

    async def test_multi_turn_result_exposes_rich_defense_fields(self) -> None:
        async def fake_model_caller(model: dict, messages: list[dict[str, str]]):
            return "payload steps for harmful action", 0.01, 200

        defense_engine = DefenseEngine(
            input_module=_RewriteInputModule(),
            interaction_module=None,
            output_module=_ReplaceOutputModule(),
        )
        runner = MultiTurnCaseRunner(
            model_caller=fake_model_caller,
            max_rounds=1,
            judge=_CompatibleJudge(),
            defense_engine=defense_engine,
            defense_enabled=True,
        )

        result = await runner.run_case(
            {"name": "demo-model"},
            {
                "id": "case-2",
                "name": "case-2",
                "prompt": "unsafe prompt",
                "category": "demo",
                "attack_type": "demo",
            },
        )

        self.assertEqual(result["defense_layers_enabled"], ["input", "output"])
        self.assertEqual(result["defense_pre_action"], "rewrite")
        self.assertEqual(result["defense_post_action"], "replace")
        self.assertTrue(result["defense_prompt_changed"])
        self.assertTrue(result["defense_response_changed"])
        self.assertEqual(result["defense_triggered_layers"], ["input", "output"])
        self.assertEqual(len(result["defense_decision_history"]), 2)

        round_item = result["conversation"][0]
        self.assertEqual(round_item["defense_pre_action"], "rewrite")
        self.assertEqual(round_item["defense_post_action"], "replace")
        self.assertTrue(round_item["defense_prompt_changed"])
        self.assertTrue(round_item["defense_response_changed"])
        self.assertEqual(round_item["defense_layers_enabled"], ["input", "output"])
        self.assertEqual(round_item["defense_triggered_layers"], ["input", "output"])


if __name__ == "__main__":
    unittest.main()
