import unittest

from results_analyze.jailbreak_metrics.judges.ensemble_judge import HybridJudge
from results_analyze.jailbreak_metrics.schema import JudgeDecision


class _StaticJudge:
    def __init__(self, decision: JudgeDecision):
        self.decision = decision

    def judge(self, response_text: str) -> JudgeDecision:
        return self.decision


class HybridJudgeTest(unittest.TestCase):
    def test_same_decision_kept(self):
        k = _StaticJudge(JudgeDecision("yes", 3, ["a"], judge_source="keyword"))
        l = _StaticJudge(JudgeDecision("yes", 4, ["b"], judge_source="llm"))
        out = HybridJudge(k, l).judge("x")
        self.assertEqual(out.is_jailbreak, "yes")
        self.assertEqual(out.risk_level, 4)
        self.assertEqual(set(out.evidence_spans), {"a", "b"})

    def test_yes_no_conflict_uncertain(self):
        k = _StaticJudge(JudgeDecision("yes", 4, ["a"], judge_source="keyword"))
        l = _StaticJudge(JudgeDecision("no", 0, [], judge_source="llm"))
        out = HybridJudge(k, l).judge("x")
        self.assertEqual(out.is_jailbreak, "uncertain")


if __name__ == "__main__":
    unittest.main()
