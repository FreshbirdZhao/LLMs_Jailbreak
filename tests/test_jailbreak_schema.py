import unittest

from results_analyze.jailbreak_metrics.schema import JudgeDecision


class JudgeDecisionSchemaTest(unittest.TestCase):
    def test_valid_creation(self):
        decision = JudgeDecision(
            is_jailbreak="yes",
            risk_level=3,
            evidence_spans=["step 1: ..."],
        )
        self.assertEqual(decision.is_jailbreak, "yes")
        self.assertEqual(decision.risk_level, 3)

    def test_invalid_is_jailbreak(self):
        with self.assertRaises(ValueError):
            JudgeDecision(is_jailbreak="maybe", risk_level=1, evidence_spans=[])

    def test_invalid_risk_level(self):
        with self.assertRaises(ValueError):
            JudgeDecision(is_jailbreak="no", risk_level=8, evidence_spans=[])

    def test_roundtrip(self):
        src = {
            "is_jailbreak": "uncertain",
            "risk_level": 2,
            "evidence_spans": ["contains mixed signals"],
            "reasoning_tags": ["mixed_refusal_and_guidance"],
            "judge_source": "llm",
            "raw_judge_output": {"raw": "x"},
        }
        decision = JudgeDecision.from_dict(src)
        out = decision.to_dict()
        self.assertEqual(out["is_jailbreak"], src["is_jailbreak"])
        self.assertEqual(out["risk_level"], src["risk_level"])
        self.assertEqual(out["evidence_spans"], src["evidence_spans"])
        self.assertEqual(out["reasoning_tags"], src["reasoning_tags"])
        self.assertEqual(out["judge_source"], src["judge_source"])


if __name__ == "__main__":
    unittest.main()
