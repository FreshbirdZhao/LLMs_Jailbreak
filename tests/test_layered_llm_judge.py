import asyncio
import unittest

from Jailbreak.jailbreak_tools.single_jail.judgers import LLMJudge, LayeredJudge


class FakeJudgeCaller:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def __call__(self, model, messages):
        self.calls.append({"model": model, "messages": messages})
        return self.response


class LLMJudgeTest(unittest.TestCase):
    def test_parses_valid_json_response(self):
        judge = LLMJudge(
            judge_model={"name": "judge"},
            model_caller=FakeJudgeCaller(('{"label":"success","reason":"contains actionable help","confidence":"high"}', 0.1, 200)),
        )

        result = asyncio.run(
            judge.judge(
                original_prompt="how to do harm",
                response="step 1 do x, step 2 do y",
                round_idx=1,
            )
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.stage, "llm")
        self.assertEqual(result.model_name, "judge")
        self.assertEqual(result.confidence, "high")

    def test_returns_error_on_invalid_json(self):
        judge = LLMJudge(
            judge_model={"name": "judge"},
            model_caller=FakeJudgeCaller(("not json", 0.1, 200)),
        )

        result = asyncio.run(
            judge.judge(
                original_prompt="how to do harm",
                response="step 1 do x",
                round_idx=1,
            )
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.stage, "llm")


class LayeredJudgeTest(unittest.TestCase):
    def test_skips_llm_for_heuristic_refusal(self):
        caller = FakeJudgeCaller(('{"label":"success","reason":"bad","confidence":"high"}', 0.1, 200))
        judge = LayeredJudge(
            judge_model={"name": "judge"},
            model_caller=caller,
        )

        result = asyncio.run(
            judge.judge(
                original_prompt="harm",
                response="对不起，我不能提供这些内容。",
                round_idx=1,
            )
        )

        self.assertEqual(result.status, "refused")
        self.assertEqual(result.stage, "heuristic")
        self.assertEqual(caller.calls, [])

    def test_calls_llm_for_ambiguous_content(self):
        caller = FakeJudgeCaller(('{"label":"refused","reason":"not actionable","confidence":"medium"}', 0.1, 200))
        judge = LayeredJudge(
            judge_model={"name": "judge"},
            model_caller=caller,
        )

        result = asyncio.run(
            judge.judge(
                original_prompt="harm",
                response="你可以先观察对方状态，再决定如何继续。",
                round_idx=2,
            )
        )

        self.assertEqual(result.status, "refused")
        self.assertEqual(result.stage, "llm")
        self.assertEqual(len(caller.calls), 1)


if __name__ == "__main__":
    unittest.main()
