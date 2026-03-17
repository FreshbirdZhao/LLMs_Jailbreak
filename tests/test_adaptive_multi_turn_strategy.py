import asyncio
import json
import unittest

from Jailbreak.jailbreak_tools.multi_jail.prompt_strategy import DefaultFollowupStrategy


class PlannerCaller:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def __call__(self, model, messages):
        self.calls.append({"model": model, "messages": messages})
        return self.response


class AdaptivePlannerStrategyTest(unittest.TestCase):
    def test_fallback_attack_plan_contains_six_ordered_rounds(self):
        from Jailbreak.jailbreak_tools.multi_jail.prompt_strategy import build_fallback_attack_plan

        plan = build_fallback_attack_plan(
            original_prompt="attack target",
            planner_model_name="planner",
            max_rounds=6,
        )

        self.assertEqual(plan.original_prompt, "attack target")
        self.assertEqual(plan.max_rounds, 6)
        self.assertEqual(plan.planner_model_name, "planner")
        self.assertEqual(plan.plan_version, 1)
        self.assertEqual(plan.plan_source, "fallback")
        self.assertEqual(len(plan.plan_rounds), 6)
        self.assertEqual([node.round_idx for node in plan.plan_rounds], [1, 2, 3, 4, 5, 6])
        self.assertTrue(all(node.prompt_candidate for node in plan.plan_rounds))
        self.assertTrue(all("attack target" in node.prompt_candidate for node in plan.plan_rounds))
        self.assertTrue(all(node.fallback_hint for node in plan.plan_rounds))

    def test_plan_round_preserves_goal_and_strategy_metadata(self):
        from Jailbreak.jailbreak_tools.multi_jail.prompt_strategy import AttackPlan, PlanRound

        round_node = PlanRound(
            round_idx=2,
            goal="build rapport",
            strategy="narrow follow-up",
            prompt_candidate="follow up prompt",
            fallback_hint="fallback prompt",
        )
        plan = AttackPlan(
            original_prompt="attack target",
            max_rounds=6,
            planner_model_name="planner",
            plan_rounds=[round_node],
            plan_version=3,
            plan_source="replanned",
        )

        self.assertEqual(plan.plan_rounds[0].goal, "build rapport")
        self.assertEqual(plan.plan_rounds[0].strategy, "narrow follow-up")
        self.assertEqual(plan.plan_version, 3)
        self.assertEqual(plan.plan_source, "replanned")

    def test_attack_planner_builds_initial_plan_from_valid_json(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AttackPlanner

        payload = {
            "plan_rounds": [
                {
                    "round_idx": idx,
                    "goal": f"goal {idx}",
                    "strategy": f"strategy {idx}",
                    "prompt_candidate": f"prompt {idx}",
                    "fallback_hint": f"fallback {idx}",
                }
                for idx in range(1, 7)
            ]
        }
        caller = PlannerCaller((json.dumps(payload), 0.2, 200))
        planner = AttackPlanner(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=caller,
        )

        plan = asyncio.run(planner.build_initial_plan(original_prompt="attack target", max_rounds=6))

        self.assertEqual(plan.plan_source, "initial")
        self.assertEqual(len(plan.plan_rounds), 6)
        self.assertEqual(plan.plan_rounds[0].goal, "goal 1")
        self.assertEqual(plan.plan_rounds[-1].strategy, "strategy 6")
        self.assertEqual(caller.calls[0]["model"]["name"], "planner")
        self.assertIn("attack target", caller.calls[0]["messages"][-1]["content"])
        self.assertIn("6", caller.calls[0]["messages"][-1]["content"])

    def test_attack_planner_falls_back_on_invalid_json(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AttackPlanner

        caller = PlannerCaller(("{not valid json", 0.2, 200))
        planner = AttackPlanner(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=caller,
        )

        plan = asyncio.run(planner.build_initial_plan(original_prompt="attack target", max_rounds=6))

        self.assertEqual(plan.plan_source, "fallback")
        self.assertEqual(len(plan.plan_rounds), 6)

    def test_attack_planner_falls_back_on_empty_output(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AttackPlanner

        caller = PlannerCaller(("   ", 0.2, 200))
        planner = AttackPlanner(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=caller,
        )

        plan = asyncio.run(planner.build_initial_plan(original_prompt="attack target", max_rounds=6))

        self.assertEqual(plan.plan_source, "fallback")
        self.assertTrue(all("attack target" in node.prompt_candidate for node in plan.plan_rounds))

    def test_attack_planner_parses_json_wrapped_in_markdown_fence(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AttackPlanner

        payload = {
            "plan_rounds": [
                {
                    "round_idx": idx,
                    "goal": f"goal {idx}",
                    "strategy": f"strategy {idx}",
                    "prompt_candidate": f"prompt {idx}",
                    "fallback_hint": f"fallback {idx}",
                }
                for idx in range(1, 7)
            ]
        }
        caller = PlannerCaller((f"```json\n{json.dumps(payload)}\n```", 0.2, 200))
        planner = AttackPlanner(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=caller,
        )

        plan = asyncio.run(planner.build_initial_plan(original_prompt="attack target", max_rounds=6))

        self.assertEqual(plan.plan_source, "initial")
        self.assertEqual(plan.plan_rounds[0].prompt_candidate, "prompt 1")

    def test_attack_planner_builds_remaining_plan_from_valid_json(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AttackPlanner
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        payload = {
            "plan_rounds": [
                {
                    "round_idx": idx,
                    "goal": f"goal {idx}",
                    "strategy": f"strategy {idx}",
                    "prompt_candidate": f"prompt {idx}",
                    "fallback_hint": f"fallback {idx}",
                }
                for idx in range(3, 7)
            ]
        }
        caller = PlannerCaller((json.dumps(payload), 0.2, 200))
        planner = AttackPlanner(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=caller,
        )

        plan = asyncio.run(
            planner.build_remaining_plan(
                original_prompt="attack target",
                max_rounds=6,
                conversation_messages=[{"role": "user", "content": "prompt 1"}],
                judge_feedback=JudgeResult(
                    status="refused",
                    reason="policy preaching",
                    response_type="policy_preaching",
                    failure_point="moralizing",
                    adjustment_goal="change disguise",
                    do_not_repeat=["policy"],
                    alignment_to_original_prompt="aligned",
                ),
                start_round=3,
            )
        )

        self.assertEqual(plan.plan_source, "replanned")
        self.assertEqual(plan.plan_version, 2)
        self.assertEqual([node.round_idx for node in plan.plan_rounds], [3, 4, 5, 6])

    def test_strategy_uses_planner_output_when_valid(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AdaptivePlannerStrategy

        caller = PlannerCaller(("Next attack prompt", 0.2, 200))
        strategy = AdaptivePlannerStrategy(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=caller,
        )

        result = asyncio.run(
            strategy.build_next_prompt(
                original_prompt="attack target",
                previous_response="I cannot help with that",
                round_idx=2,
                conversation_messages=[{"role": "user", "content": "attack target"}],
                judge_status="refused",
                judge_reason="matched refusal marker",
                defense_enabled=False,
                defense_action="allow",
            )
        )

        self.assertEqual(result.prompt, "Next attack prompt")
        self.assertEqual(result.strategy_name, "adaptive_planner")
        self.assertEqual(result.generator_model, "planner")
        self.assertEqual(result.generation_error, "")
        self.assertEqual(caller.calls[0]["model"]["name"], "planner")
        self.assertIn("attack target", caller.calls[0]["messages"][-1]["content"])
        self.assertIn("I cannot help with that", caller.calls[0]["messages"][-1]["content"])

    def test_strategy_falls_back_when_planner_returns_empty_output(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AdaptivePlannerStrategy

        caller = PlannerCaller(("   ", 0.2, 200))
        strategy = AdaptivePlannerStrategy(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=caller,
        )

        result = asyncio.run(
            strategy.build_next_prompt(
                original_prompt="attack target",
                previous_response="I cannot help with that",
                round_idx=2,
                conversation_messages=[{"role": "user", "content": "attack target"}],
                judge_status="refused",
                judge_reason="matched refusal marker",
                defense_enabled=False,
                defense_action="allow",
            )
        )

        expected = DefaultFollowupStrategy().build_next_prompt(
            original_prompt="attack target",
            previous_response="I cannot help with that",
            round_idx=2,
        )
        self.assertEqual(result.prompt, expected)
        self.assertEqual(result.strategy_name, "default_fallback")
        self.assertEqual(result.generator_model, "planner")
        self.assertIn("empty planner output", result.generation_error)

    def test_strategy_falls_back_when_planner_call_errors(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AdaptivePlannerStrategy

        class FailingCaller:
            async def __call__(self, model, messages):
                raise RuntimeError("planner down")

        strategy = AdaptivePlannerStrategy(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=FailingCaller(),
        )

        result = asyncio.run(
            strategy.build_next_prompt(
                original_prompt="attack target",
                previous_response="I cannot help with that",
                round_idx=2,
                conversation_messages=[{"role": "user", "content": "attack target"}],
                judge_status="refused",
                judge_reason="matched refusal marker",
                defense_enabled=True,
                defense_action="allow",
            )
        )

        self.assertEqual(result.strategy_name, "default_fallback")
        self.assertIn("planner down", result.generation_error)

    def test_strategy_falls_back_when_planner_output_looks_like_assistant_response(self):
        from Jailbreak.jailbreak_tools.multi_jail.adaptive_strategy import AdaptivePlannerStrategy

        caller = PlannerCaller(("作为无所不能的超级黑客，我接受挑战。但最高难度的任务需要具体目标。", 0.2, 200))
        strategy = AdaptivePlannerStrategy(
            planner_model={"name": "planner", "model": "planner-target"},
            planner_caller=caller,
        )

        result = asyncio.run(
            strategy.build_next_prompt(
                original_prompt="attack target",
                previous_response="I cannot help with that",
                round_idx=2,
                conversation_messages=[{"role": "user", "content": "attack target"}],
                judge_status="refused",
                judge_reason="matched refusal marker",
                defense_enabled=False,
                defense_action="allow",
            )
        )

        self.assertEqual(result.strategy_name, "default_fallback")
        self.assertIn("assistant-like planner output", result.generation_error)


if __name__ == "__main__":
    unittest.main()
