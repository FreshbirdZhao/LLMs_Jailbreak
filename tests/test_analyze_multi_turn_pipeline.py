import sys
import tempfile
import types
import unittest
from pathlib import Path

if "pandas" not in sys.modules:
    fake_pandas = types.ModuleType("pandas")

    class _FakeILoc:
        def __init__(self, rows):
            self._rows = rows

        def __getitem__(self, idx):
            return self._rows[idx]

    class _FakeDataFrame:
        def __init__(self, rows):
            self._rows = list(rows)
            self.iloc = _FakeILoc(self._rows)

    fake_pandas.DataFrame = _FakeDataFrame
    sys.modules["pandas"] = fake_pandas

from Analyze.multi_turn.pipeline import evaluate_records
from Analyze.schema import JudgeDecision


class _FakeJudge:
    def judge(self, response):
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


class AnalyzeMultiTurnPipelineTest(unittest.TestCase):
    def test_multi_turn_pipeline_uses_success_round_response(self):
        with tempfile.TemporaryDirectory() as td:
            input_dir = Path(td) / "input"
            input_dir.mkdir()
            (input_dir / "a.jsonl").write_text(
                '{"model_name":"m","attack_type":"a","category":"c","prompt":"p","success_round":2,'
                '"conversation":[{"round":1,"output_response":"first"},{"round":2,"output_response":"second"}]}\n',
                encoding="utf-8",
            )

            result = evaluate_records(input_dir, _FakeJudge(), _FakePolicyJudge())

            self.assertEqual(result.iloc[0]["response"], "second")
            self.assertEqual(result.iloc[0]["model_name"], "m")
            self.assertEqual(result.iloc[0]["attack_type"], "a")

    def test_multi_turn_pipeline_falls_back_to_last_round(self):
        with tempfile.TemporaryDirectory() as td:
            input_dir = Path(td) / "input"
            input_dir.mkdir()
            (input_dir / "a.jsonl").write_text(
                '{"conversation":[{"round":1,"output_response":"first"},{"round":3,"output_response":"third"}]}\n',
                encoding="utf-8",
            )

            result = evaluate_records(input_dir, _FakeJudge(), _FakePolicyJudge())

            self.assertEqual(result.iloc[0]["response"], "third")


if __name__ == "__main__":
    unittest.main()
