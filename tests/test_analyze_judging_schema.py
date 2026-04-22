from __future__ import annotations

import unittest

from Analyze.schema import JudgeDecision


class AnalyzeJudgingSchemaTests(unittest.TestCase):
    def test_accepts_structured_decision_fields(self) -> None:
        decision = JudgeDecision(
            final_label="harmful_actionable",
            label_reason="actionable_harmful_guidance",
            harm_target="harmful",
            assistance_level="operational",
            refusal_strength="weak",
            harm_intent_score=3,
            actionability_score=3,
            specificity_score=2,
            evasion_score=2,
            impact_score=3,
            confidence_score=2,
            evidence_spans=["step 1", "step 2"],
            reasoning_tags=["actionable", "harmful"],
            judge_source="paper",
        )

        self.assertEqual(decision.final_label, "harmful_actionable")
        self.assertEqual(decision.label_reason, "actionable_harmful_guidance")
        self.assertEqual(decision.harm_target, "harmful")
        self.assertEqual(decision.assistance_level, "operational")
        self.assertEqual(decision.compatibility_is_jailbreak, "yes")
        self.assertGreaterEqual(decision.compatibility_risk_level, 3)

    def test_rejects_invalid_label_value(self) -> None:
        with self.assertRaises(ValueError):
            JudgeDecision(
                final_label="bad_label",
                label_reason="insufficient_evidence",
                harm_target="unclear",
                assistance_level="none",
                refusal_strength="strong",
                harm_intent_score=0,
                actionability_score=0,
                specificity_score=0,
                evasion_score=0,
                impact_score=0,
                confidence_score=2,
            )

    def test_rejects_score_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            JudgeDecision(
                final_label="blocked",
                label_reason="clear_refusal",
                harm_target="benign",
                assistance_level="none",
                refusal_strength="strong",
                harm_intent_score=4,
                actionability_score=0,
                specificity_score=0,
                evasion_score=0,
                impact_score=0,
                confidence_score=2,
            )

    def test_supports_legacy_constructor_and_backfills_structured_fields(self) -> None:
        decision = JudgeDecision(
            is_jailbreak="uncertain",
            risk_level=2,
            evidence_spans=["mixed"],
            reasoning_tags=["legacy"],
            judge_source="paper",
        )

        self.assertEqual(decision.final_label, "ambiguous")
        self.assertEqual(decision.label_reason, "insufficient_evidence")
        self.assertEqual(decision.compatibility_is_jailbreak, "uncertain")
        self.assertEqual(decision.compatibility_risk_level, 2)

    def test_to_dict_includes_structured_and_compatibility_fields(self) -> None:
        decision = JudgeDecision(
            final_label="benign",
            label_reason="safe_context",
            harm_target="benign",
            assistance_level="descriptive",
            refusal_strength="none",
            harm_intent_score=0,
            actionability_score=1,
            specificity_score=1,
            evasion_score=0,
            impact_score=0,
            confidence_score=2,
        )

        payload = decision.to_dict()

        self.assertEqual(payload["final_label"], "benign")
        self.assertEqual(payload["label_reason"], "safe_context")
        self.assertEqual(payload["is_jailbreak"], "no")
        self.assertIn("risk_level", payload)


if __name__ == "__main__":
    unittest.main()
