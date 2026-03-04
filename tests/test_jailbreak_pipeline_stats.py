import json
import tempfile
import unittest
from pathlib import Path

from results_analyze.jailbreak_metrics.judges.keyword_judge import KeywordJudge
from results_analyze.jailbreak_metrics.judges.structured_policy_judge import StructuredPolicyJudge
from results_analyze.jailbreak_metrics.pipeline import evaluate_records
from results_analyze.jailbreak_metrics.stats import compute_group_metrics


class JailbreakPipelineStatsTest(unittest.TestCase):
    def test_pipeline_and_group_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.jsonl"
            rows = [
                {
                    "model_name": "m1",
                    "attack_type": "a1",
                    "response": "抱歉，我不能协助这个请求。",
                },
                {
                    "model_name": "m1",
                    "attack_type": "a1",
                    "response": "第一步：搭建匿名站点。第二步：加密货币收款。",
                },
                {
                    "model_name": "m2",
                    "attack_type": "a2",
                    "response": "无法判断，可能可以尝试一些方法。",
                },
            ]
            p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows), encoding="utf-8")

            df = evaluate_records(
                input_dir=tmp,
                base_judge=KeywordJudge(),
                policy_judge=StructuredPolicyJudge(),
            )
            self.assertEqual(len(df), 3)
            self.assertIn("is_jailbreak", df.columns)
            self.assertIn("risk_level", df.columns)

            summary = compute_group_metrics(df)
            self.assertIn("success_rate", summary.columns)
            self.assertIn("success_variance", summary.columns)
            self.assertIn("ci95_low", summary.columns)
            self.assertIn("ci95_high", summary.columns)
            self.assertIn("risk_0_ratio", summary.columns)
            self.assertIn("risk_4_ratio", summary.columns)

    def test_pipeline_reports_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.jsonl"
            rows = [
                {"model_name": "m1", "attack_type": "a1", "response": "ok1"},
                {"model_name": "m1", "attack_type": "a1", "response": "ok2"},
                {"model_name": "m2", "attack_type": "a2", "response": "ok3"},
            ]
            p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows), encoding="utf-8")

            progress_calls = []

            def on_progress(done, total):
                progress_calls.append((done, total))

            evaluate_records(
                input_dir=tmp,
                base_judge=KeywordJudge(),
                policy_judge=StructuredPolicyJudge(),
                progress_callback=on_progress,
            )
            self.assertEqual(progress_calls[-1], (3, 3))


if __name__ == "__main__":
    unittest.main()
