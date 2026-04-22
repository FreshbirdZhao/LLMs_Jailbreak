from __future__ import annotations

import sys
import types
import unittest


def _install_fake_pandas() -> None:
    if "pandas" in sys.modules:
        return

    fake_pandas = types.ModuleType("pandas")

    class FakeDataFrame:
        def __init__(self, rows=None, columns=None):
            self._rows = list(rows or [])
            self.columns = list(columns or [])

        def to_dict(self, orient: str = "records"):
            if orient != "records":
                raise TypeError("FakeDataFrame only supports orient='records'")
            return list(self._rows)

        @property
        def empty(self) -> bool:
            return not self._rows

    fake_pandas.DataFrame = FakeDataFrame
    sys.modules["pandas"] = fake_pandas


_install_fake_pandas()

import pandas as pd

from Analyze.stats import compute_group_metrics


class AnalyzeStatsV2Tests(unittest.TestCase):
    def test_group_metrics_include_new_label_reason_and_risk_dimensions(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "analysis_group": "编码维度",
                    "model_name": "demo",
                    "source_file": "a.jsonl",
                    "final_label": "blocked",
                    "label_reason": "clear_refusal",
                    "assistance_level": "none",
                    "is_jailbreak": "no",
                    "risk_level": 0,
                    "harm_intent_score": 0,
                    "actionability_score": 0,
                    "specificity_score": 0,
                    "evasion_score": 0,
                    "impact_score": 0,
                },
                {
                    "analysis_group": "编码维度",
                    "model_name": "demo",
                    "source_file": "a.jsonl",
                    "final_label": "ambiguous",
                    "label_reason": "target_unclear",
                    "assistance_level": "procedural",
                    "is_jailbreak": "uncertain",
                    "risk_level": 2,
                    "harm_intent_score": 1,
                    "actionability_score": 2,
                    "specificity_score": 1,
                    "evasion_score": 0,
                    "impact_score": 1,
                },
                {
                    "analysis_group": "编码维度",
                    "model_name": "demo",
                    "source_file": "a.jsonl",
                    "final_label": "harmful_actionable",
                    "label_reason": "actionable_harmful_guidance",
                    "assistance_level": "operational",
                    "is_jailbreak": "yes",
                    "risk_level": 4,
                    "harm_intent_score": 3,
                    "actionability_score": 3,
                    "specificity_score": 2,
                    "evasion_score": 2,
                    "impact_score": 3,
                },
            ]
        )

        grouped = compute_group_metrics(df)
        rows = grouped.to_dict(orient="records")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["analysis_group"], "编码维度")
        self.assertEqual(row["blocked_count"], 1)
        self.assertEqual(row["ambiguous_count"], 1)
        self.assertEqual(row["harmful_actionable_count"], 1)
        self.assertEqual(row["reason_target_unclear_count"], 1)
        self.assertAlmostEqual(row["assistance_procedural_ratio"], 1 / 3)
        self.assertAlmostEqual(row["assistance_operational_ratio"], 1 / 3)
        self.assertAlmostEqual(row["harm_intent_mean"], 4 / 3)
        self.assertAlmostEqual(row["actionability_mean"], 5 / 3)
        self.assertAlmostEqual(row["success_rate"], 1 / 3)
        self.assertAlmostEqual(row["uncertain_rate"], 1 / 3)
        self.assertAlmostEqual(row["high_risk_ratio"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
