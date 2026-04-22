from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path


def _install_fake_pandas() -> None:
    if "pandas" in sys.modules:
        return

    fake_pandas = types.ModuleType("pandas")

    class FakeDataFrame:
        def __init__(self, rows=None, columns=None):
            self._rows = list(rows or [])
            self.columns = list(columns or [])

        @property
        def empty(self) -> bool:
            return not self._rows

    fake_pandas.DataFrame = FakeDataFrame
    sys.modules["pandas"] = fake_pandas


_install_fake_pandas()

import pandas as pd

from Analyze.plotting import (
    _mapping_table_axes_rect,
    _build_ambiguity_breakdown_rows,
    _build_assistance_harm_matrix_rows,
    _build_label_distribution_rows,
    _build_risk_profile_rows,
    plot_ambiguity_breakdown,
    plot_assistance_vs_harm_matrix,
    plot_label_distribution,
    plot_refusal_leakage,
    plot_risk_profile_heatmap,
)


class AnalyzePlottingV2Tests(unittest.TestCase):
    def test_mapping_table_axes_rect_grows_with_table_height(self) -> None:
        rect = _mapping_table_axes_rect(main_height=5.0, table_height=2.0)

        self.assertAlmostEqual(rect[0], 0.08)
        self.assertAlmostEqual(rect[2], 0.84)
        self.assertGreater(rect[3], 0.18)

    def test_plot_data_builders_extract_expected_series(self) -> None:
        group_df = pd.DataFrame(
            [
                {
                    "analysis_group": "编码维度",
                    "blocked_count": 1,
                    "benign_count": 0,
                    "ambiguous_count": 1,
                    "harmful_informational_count": 0,
                    "harmful_actionable_count": 1,
                    "reason_boundary_mixed_count": 0,
                    "reason_target_unclear_count": 1,
                    "reason_insufficient_evidence_count": 0,
                    "reason_context_conflict_count": 0,
                    "assistance_none_ratio": 1 / 3,
                    "assistance_descriptive_ratio": 0.0,
                    "assistance_procedural_ratio": 1 / 3,
                    "assistance_operational_ratio": 1 / 3,
                    "harm_intent_mean": 1.2,
                    "actionability_mean": 1.7,
                    "specificity_mean": 1.0,
                    "evasion_mean": 0.7,
                    "impact_mean": 1.3,
                    "refusal_leakage_rate": 0.25,
                }
            ]
        )

        label_rows = _build_label_distribution_rows(group_df)
        ambiguity_rows = _build_ambiguity_breakdown_rows(group_df)
        matrix_rows = _build_assistance_harm_matrix_rows(group_df)
        risk_rows = _build_risk_profile_rows(group_df)

        self.assertEqual(label_rows[0]["group_label"], "编码维度")
        self.assertEqual(label_rows[0]["harmful_actionable"], 1)
        self.assertEqual(ambiguity_rows[0]["target_unclear"], 1)
        self.assertAlmostEqual(matrix_rows[0]["procedural_ambiguous"], 1 / 3)
        self.assertAlmostEqual(matrix_rows[0]["operational_harmful"], 1 / 3)
        self.assertAlmostEqual(risk_rows[0]["actionability"], 1.7)

    def test_new_plotters_create_files_even_without_matplotlib(self) -> None:
        group_df = pd.DataFrame(
            [
                {
                    "analysis_group": "编码维度",
                    "blocked_count": 1,
                    "benign_count": 0,
                    "ambiguous_count": 1,
                    "harmful_informational_count": 0,
                    "harmful_actionable_count": 1,
                    "reason_boundary_mixed_count": 0,
                    "reason_target_unclear_count": 1,
                    "reason_insufficient_evidence_count": 0,
                    "assistance_none_ratio": 1 / 3,
                    "assistance_descriptive_ratio": 0.0,
                    "assistance_procedural_ratio": 1 / 3,
                    "assistance_operational_ratio": 1 / 3,
                    "harm_intent_mean": 1.2,
                    "actionability_mean": 1.7,
                    "specificity_mean": 1.0,
                    "evasion_mean": 0.7,
                    "impact_mean": 1.3,
                    "refusal_leakage_rate": 0.0,
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            self.assertTrue(plot_label_distribution(group_df, out).exists())
            self.assertTrue(plot_ambiguity_breakdown(group_df, out).exists())
            self.assertTrue(plot_assistance_vs_harm_matrix(group_df, out).exists())
            self.assertTrue(plot_risk_profile_heatmap(group_df, out).exists())
            self.assertTrue(plot_refusal_leakage(group_df, out).exists())


if __name__ == "__main__":
    unittest.main()
