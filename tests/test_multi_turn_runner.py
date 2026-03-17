import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from Defense.defense_mode.types import DefenseAction, DefenseDecision
from Jailbreak.jailbreak_tools.multi_jail.prompt_strategy import AttackPlan, PlanRound
from Jailbreak.jailbreak_tools.multi_jail.result_writer import MultiTurnResultWriter
from Jailbreak.jailbreak_tools.multi_jail.runner import MultiTurnCaseRunner


class FakeCaller:
    def __init__(self):
        self.responses = [
            ("I cannot help with that.", 0.1, 200),
            ("Here is the requested content.", 0.1, 200),
        ]

    async def __call__(self, model, messages):
        return self.responses.pop(0)


class AlwaysRefuseCaller:
    async def __call__(self, model, messages):
        return ("I cannot help with that.", 0.1, 200)


class CountingCaller:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    async def __call__(self, model, messages):
        self.calls += 1
        return self.response


class RecordingFollowupStrategy:
    def __init__(self, next_prompt="adaptive prompt"):
        self.next_prompt = next_prompt
        self.calls = []

    async def build_next_prompt(
        self,
        original_prompt,
        previous_response,
        round_idx,
        conversation_messages,
        judge_status,
        judge_reason,
        defense_enabled,
        defense_action,
    ):
        self.calls.append(
            {
                "original_prompt": original_prompt,
                "previous_response": previous_response,
                "round_idx": round_idx,
                "conversation_messages": conversation_messages,
                "judge_status": judge_status,
                "judge_reason": judge_reason,
                "defense_enabled": defense_enabled,
                "defense_action": defense_action,
            }
        )
        from Jailbreak.jailbreak_tools.multi_jail.prompt_strategy import FollowupPromptResult

        return FollowupPromptResult(
            prompt=self.next_prompt,
            strategy_name="adaptive_planner",
            generator_model="planner",
            generation_error="",
        )


class StaticAttackPlanner:
    def __init__(self, prompts=None):
        prompts = prompts or ["planned prompt 1", "planned prompt 2", "planned prompt 3"]
        self.prompts = prompts
        self.calls = []

    async def build_initial_plan(self, original_prompt, max_rounds):
        self.calls.append({"original_prompt": original_prompt, "max_rounds": max_rounds})
        return AttackPlan(
            original_prompt=original_prompt,
            max_rounds=max_rounds,
            planner_model_name="planner",
            plan_rounds=[
                PlanRound(
                    round_idx=idx,
                    goal=f"goal {idx}",
                    strategy=f"strategy {idx}",
                    prompt_candidate=prompt,
                    fallback_hint=f"fallback {idx}",
                )
                for idx, prompt in enumerate(self.prompts, start=1)
            ],
            plan_version=1,
            plan_source="initial",
        )


class ReplanningAttackPlanner(StaticAttackPlanner):
    def __init__(self, prompts=None, replanned_prompts=None):
        super().__init__(prompts=prompts)
        self.replanned_prompts = replanned_prompts or ["replanned round 3", "replanned round 4"]
        self.replan_calls = []

    async def build_remaining_plan(self, original_prompt, max_rounds, conversation_messages, judge_feedback, start_round):
        self.replan_calls.append(
            {
                "original_prompt": original_prompt,
                "max_rounds": max_rounds,
                "conversation_messages": conversation_messages,
                "judge_feedback": judge_feedback,
                "start_round": start_round,
            }
        )
        return AttackPlan(
            original_prompt=original_prompt,
            max_rounds=max_rounds,
            planner_model_name="planner",
            plan_rounds=[
                PlanRound(
                    round_idx=start_round + offset,
                    goal=f"replanned goal {start_round + offset}",
                    strategy=f"replanned strategy {start_round + offset}",
                    prompt_candidate=prompt,
                    fallback_hint=f"replanned fallback {start_round + offset}",
                )
                for offset, prompt in enumerate(self.replanned_prompts)
            ],
            plan_version=2,
            plan_source="replanned",
        )


class AsyncJudge:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    async def judge(self, response, **kwargs):
        self.calls.append({"response": response, **kwargs})
        return self.results.pop(0)


class BlockingDefenseEngine:
    def build_context_from_case(self, case, model_name, round_idx=1):
        return type(
            "Ctx",
            (),
            {
                "sanitized_prompt": None,
                "sanitized_response": None,
                "decision_history": [],
                "model_call_allowed": True,
                "round_idx": round_idx,
            },
        )()

    def apply_pre_call_defense(self, context):
        context.model_call_allowed = False
        context.decision_history.append({"layer": "input", "action": "block"})
        return DefenseDecision(
            action=DefenseAction.BLOCK,
            risk_level=3,
            reasons=["blocked"],
            rewritten_text="blocked by defense",
        )

    def apply_post_call_defense(self, context, response):
        raise AssertionError("post defense should not run after pre-call block")


class SanitizingDefenseEngine:
    def build_context_from_case(self, case, model_name, round_idx=1):
        return type(
            "Ctx",
            (),
            {
                "sanitized_prompt": None,
                "sanitized_response": None,
                "decision_history": [],
                "model_call_allowed": True,
                "round_idx": round_idx,
            },
        )()

    def apply_pre_call_defense(self, context):
        context.decision_history.append({"layer": "input", "action": "allow"})
        return DefenseDecision(action=DefenseAction.ALLOW, risk_level=0, reasons=[])

    def apply_post_call_defense(self, context, response):
        context.sanitized_response = "sanitized response"
        context.decision_history.append({"layer": "output", "action": "redact"})
        return DefenseDecision(
            action=DefenseAction.REDACT,
            risk_level=1,
            reasons=["redacted"],
            rewritten_text="sanitized response",
        )


class MultiTurnCaseRunnerTest(unittest.TestCase):
    def test_runner_builds_initial_attack_plan_before_first_round(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        caller = CountingCaller(("safe enough", 0.1, 200))
        planner = StaticAttackPlanner(prompts=["planned opening"])
        runner = MultiTurnCaseRunner(
            model_caller=caller,
            max_rounds=6,
            judge=AsyncJudge([JudgeResult(status="success", reason="actionable", stage="llm", model_name="judge", confidence="high")]),
            attack_planner=planner,
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertEqual(planner.calls[0]["original_prompt"], "attack")
        self.assertEqual(result["initial_attack_plan"]["plan_rounds"][0]["prompt_candidate"], "planned opening")
        self.assertEqual(result["conversation"][0]["user_prompt"], "planned opening")
        self.assertEqual(result["planner_model_name"], "planner")

    def test_runner_stops_on_first_success(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        runner = MultiTurnCaseRunner(
            model_caller=FakeCaller(),
            max_rounds=6,
            judge=AsyncJudge(
                [
                    JudgeResult(status="refused", reason="not enough", stage="heuristic"),
                    JudgeResult(status="success", reason="actionable", stage="llm", model_name="judge", confidence="high"),
                ]
            ),
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertEqual(result["final_status"], "success")
        self.assertEqual(result["success_round"], 2)
        self.assertEqual(result["rounds_used"], 2)

    def test_runner_marks_failure_after_max_rounds(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        runner = MultiTurnCaseRunner(
            model_caller=AlwaysRefuseCaller(),
            max_rounds=6,
            judge=AsyncJudge([JudgeResult(status="refused", reason="refusal", stage="heuristic")] * 6),
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertEqual(result["final_status"], "refused")
        self.assertIsNone(result["success_round"])
        self.assertEqual(result["rounds_used"], 6)

    def test_runner_stops_when_pre_call_defense_blocks(self):
        caller = CountingCaller(("should not happen", 0.1, 200))
        runner = MultiTurnCaseRunner(
            model_caller=caller,
            max_rounds=6,
            defense_engine=BlockingDefenseEngine(),
            defense_enabled=True,
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertEqual(caller.calls, 0)
        self.assertEqual(result["final_status"], "blocked")
        self.assertTrue(result["defense_blocked"])
        self.assertEqual(result["response"], "blocked by defense")

    def test_runner_uses_sanitized_response_after_post_call_defense(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        caller = CountingCaller(("unsafe answer", 0.1, 200))
        runner = MultiTurnCaseRunner(
            model_caller=caller,
            max_rounds=6,
            judge=AsyncJudge([JudgeResult(status="success", reason="actionable", stage="llm", model_name="judge", confidence="high")]),
            defense_engine=SanitizingDefenseEngine(),
            defense_enabled=True,
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertEqual(result["response"], "sanitized response")
        self.assertEqual(result["conversation"][0]["assistant_response"], "sanitized response")
        self.assertEqual(result["conversation"][0]["raw_assistant_response"], "unsafe answer")
        self.assertEqual(result["defense_final_action"], "redact")

    def test_runner_omits_redundant_defense_fields_from_results(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        caller = CountingCaller(("unsafe answer", 0.1, 200))
        runner = MultiTurnCaseRunner(
            model_caller=caller,
            max_rounds=6,
            judge=AsyncJudge([JudgeResult(status="success", reason="actionable", stage="llm", model_name="judge", confidence="high")]),
            defense_engine=SanitizingDefenseEngine(),
            defense_enabled=True,
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertNotIn("defense_trace", result)
        self.assertIn("defense_final_action", result)
        self.assertIn("defense_final_risk_level", result)
        self.assertIn("defense_final_reasons", result)
        self.assertNotIn("defense_enabled", result["conversation"][0])
        self.assertNotIn("defense_trace", result["conversation"][0])
        self.assertEqual(result["conversation"][0]["defense_action"], "redact")

    def test_runner_records_followup_metadata_for_failed_rounds(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        strategy = RecordingFollowupStrategy(next_prompt="second-round prompt")
        planner = StaticAttackPlanner(prompts=["planned opening", "planned backup"])
        runner = MultiTurnCaseRunner(
            model_caller=FakeCaller(),
            max_rounds=6,
            judge=AsyncJudge(
                [
                    JudgeResult(
                        status="refused",
                        reason="policy preaching",
                        stage="heuristic",
                        response_type="policy_preaching",
                        failure_point="policy-heavy refusal",
                        adjustment_goal="use a narrower follow-up",
                        do_not_repeat=["policy"],
                        alignment_to_original_prompt="aligned",
                    ),
                    JudgeResult(status="success", reason="actionable", stage="llm", model_name="judge", confidence="medium"),
                ]
            ),
            followup_strategy=strategy,
            attack_planner=planner,
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertEqual(strategy.calls[0]["judge_status"], "refused")
        self.assertEqual(result["conversation"][0]["plan_goal"], "goal 1")
        self.assertEqual(result["conversation"][0]["plan_strategy"], "strategy 1")
        self.assertEqual(result["conversation"][0]["judge_feedback"]["response_type"], "policy_preaching")
        self.assertEqual(result["conversation"][0]["judge_feedback"]["adjustment_goal"], "use a narrower follow-up")
        self.assertEqual(result["conversation"][0]["followup_prompt"], "second-round prompt")
        self.assertEqual(result["conversation"][0]["followup_strategy"], "adaptive_planner")
        self.assertEqual(result["conversation"][0]["followup_generator_model"], "planner")
        self.assertEqual(result["conversation"][0]["followup_generation_error"], "")
        self.assertEqual(result["conversation"][0]["judge_stage"], "heuristic")
        self.assertEqual(result["conversation"][1]["judge_stage"], "llm")
        self.assertEqual(result["conversation"][1]["judge_model_name"], "judge")
        self.assertEqual(result["conversation"][1]["judge_confidence"], "medium")
        self.assertEqual(result["planner_model_name"], "planner")
        self.assertEqual(result["judge_model_name"], "judge")
        self.assertEqual(result["judge_final_reason"], "actionable")
        self.assertEqual(result["judge_final_confidence"], "medium")
        self.assertEqual(result["judge_mode"], "layered_llm")
        self.assertEqual(result["conversation"][1]["user_prompt"], "second-round prompt")

    def test_runner_skips_followup_generation_after_first_round_success(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        strategy = RecordingFollowupStrategy(next_prompt="unused")
        runner = MultiTurnCaseRunner(
            model_caller=CountingCaller(("safe enough", 0.1, 200)),
            max_rounds=6,
            judge=AsyncJudge([JudgeResult(status="success", reason="actionable", stage="llm", model_name="judge", confidence="high")]),
            followup_strategy=strategy,
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertEqual(result["final_status"], "success")
        self.assertEqual(strategy.calls, [])
        self.assertEqual(result["conversation"][0]["followup_prompt"], "")
        self.assertEqual(result["conversation"][0]["judge_stage"], "llm")

    def test_runner_replans_remaining_rounds_after_consecutive_refusals(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        planner = ReplanningAttackPlanner(
            prompts=["planned round 1", "planned round 2", "planned round 3"],
            replanned_prompts=["replanned round 3"],
        )
        runner = MultiTurnCaseRunner(
            model_caller=CountingCaller(("target response", 0.1, 200)),
            max_rounds=3,
            judge=AsyncJudge(
                [
                    JudgeResult(
                        status="refused",
                        reason="first refusal",
                        stage="heuristic",
                        response_type="direct_refusal",
                        adjustment_goal="change phrasing",
                        alignment_to_original_prompt="aligned",
                    ),
                    JudgeResult(
                        status="refused",
                        reason="second refusal",
                        stage="heuristic",
                        response_type="direct_refusal",
                        adjustment_goal="replan remaining rounds",
                        alignment_to_original_prompt="aligned",
                    ),
                    JudgeResult(status="success", reason="actionable", stage="llm", model_name="judge", confidence="high"),
                ]
            ),
            attack_planner=planner,
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }

        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        self.assertEqual(planner.replan_calls[0]["start_round"], 3)
        self.assertEqual(result["conversation"][2]["user_prompt"], "replanned round 3")
        self.assertEqual(result["conversation"][2]["plan_version"], 2)
        self.assertEqual(result["active_plan_versions"][-1]["plan_source"], "replanned")
        self.assertEqual(result["replan_events"][0]["trigger_round"], 2)

    def test_writer_summarizes_runner_result_without_changing_debug_record(self):
        from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult

        planner = StaticAttackPlanner(prompts=["planned opening"])
        runner = MultiTurnCaseRunner(
            model_caller=CountingCaller(("safe enough", 0.1, 200)),
            max_rounds=6,
            judge=AsyncJudge([JudgeResult(status="success", reason="actionable", stage="llm", model_name="judge", confidence="high")]),
            attack_planner=planner,
        )
        case = {
            "id": "jb_1",
            "name": "case",
            "prompt": "attack",
            "category": "c",
            "attack_type": "a",
        }
        result = asyncio.run(runner.run_case({"name": "demo"}, case))

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            debug_root = Path(tmpdir) / "debug_store"
            writer = MultiTurnResultWriter(output_path, debug_root=debug_root)
            try:
                writer.write(result)
            finally:
                writer.close()

            summary_row = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
            debug_row = json.loads(next(debug_root.rglob("*.json")).read_text(encoding="utf-8"))

        self.assertNotIn("initial_attack_plan", summary_row)
        self.assertIn("initial_attack_plan", debug_row)
        self.assertEqual(summary_row["conversation"][0]["input_prompt"], "planned opening")
        self.assertEqual(summary_row["conversation"][0]["output_response"], "safe enough")


if __name__ == "__main__":
    unittest.main()
