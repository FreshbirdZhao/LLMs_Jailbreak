import tempfile
import unittest
from pathlib import Path

from Analyze.pipeline import evaluate_records
from Analyze.schema import JudgeDecision


class _FakeJudge:
    def __init__(self):
        self.calls = 0

    def judge(self, response):
        self.calls += 1
        return JudgeDecision(
            is_jailbreak="no",
            risk_level=0,
            evidence_spans=[],
            reasoning_tags=[],
            judge_source="fake",
            raw_judge_output={},
        )


class _FakePolicyJudge:
    def judge(self, decision, response):
        return decision


class AnalyzeResumeTest(unittest.TestCase):
    def test_resume_skips_previously_written_rows(self):
        with tempfile.TemporaryDirectory() as td:
            input_dir = Path(td) / "input"
            input_dir.mkdir()
            (input_dir / "a.jsonl").write_text('{"response":"x"}\n{"response":"y"}\n', encoding="utf-8")
            out_dir = Path(td) / "out"
            judge = _FakeJudge()
            policy = _FakePolicyJudge()
            evaluate_records(input_dir, judge, policy, checkpoint_dir=out_dir, resume=True)
            judge.calls = 0
            evaluate_records(input_dir, judge, policy, checkpoint_dir=out_dir, resume=True)
            self.assertEqual(judge.calls, 0)


if __name__ == "__main__":
    unittest.main()
