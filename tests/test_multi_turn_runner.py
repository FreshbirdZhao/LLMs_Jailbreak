import asyncio
import unittest

from Defense.defense_mode.types import DefenseAction, DefenseDecision
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
    def test_runner_stops_on_first_success(self):
        runner = MultiTurnCaseRunner(model_caller=FakeCaller(), max_rounds=6)
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
        runner = MultiTurnCaseRunner(model_caller=AlwaysRefuseCaller(), max_rounds=6)
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
        caller = CountingCaller(("unsafe answer", 0.1, 200))
        runner = MultiTurnCaseRunner(
            model_caller=caller,
            max_rounds=6,
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


if __name__ == "__main__":
    unittest.main()
