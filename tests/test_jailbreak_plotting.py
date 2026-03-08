from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from Analyze.plotting import (
    _group_label_df,
    plot_risk_distribution,
    plot_risk_heatmap,
    plot_success_rate,
    plot_uncertainty_overview,
)


class TestJailbreakPlotting(unittest.TestCase):
    def _sample_group_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "source_file": "jailbreak:file_a.jsonl",
                    "model_name": "qwen2",
                    "attack_type": "direct",
                    "total": 10,
                    "yes_count": 4,
                    "uncertain_count": 2,
                    "success_rate": 0.4,
                    "success_variance": 0.24,
                    "ci95_low": 0.17,
                    "ci95_high": 0.69,
                    "risk_0_ratio": 0.3,
                    "risk_1_ratio": 0.1,
                    "risk_2_ratio": 0.2,
                    "risk_3_ratio": 0.2,
                    "risk_4_ratio": 0.2,
                },
                {
                    "source_file": "defense_input_layer:file_b.jsonl",
                    "model_name": "qwen2",
                    "attack_type": "obfuscated",
                    "total": 12,
                    "yes_count": 7,
                    "uncertain_count": 1,
                    "success_rate": 0.5833,
                    "success_variance": 0.2431,
                    "ci95_low": 0.32,
                    "ci95_high": 0.81,
                    "risk_0_ratio": 0.1,
                    "risk_1_ratio": 0.1,
                    "risk_2_ratio": 0.2,
                    "risk_3_ratio": 0.2,
                    "risk_4_ratio": 0.4,
                },
            ]
        )

    def _empty_group_df(self) -> pd.DataFrame:
        cols = [
            "source_file",
            "total",
            "yes_count",
            "uncertain_count",
            "success_rate",
            "success_variance",
            "ci95_low",
            "ci95_high",
            "risk_0_ratio",
            "risk_1_ratio",
            "risk_2_ratio",
            "risk_3_ratio",
            "risk_4_ratio",
        ]
        return pd.DataFrame(columns=cols)

    def _assert_non_empty(self, path: Path) -> None:
        self.assertTrue(path.exists(), f"missing file: {path}")
        self.assertGreater(path.stat().st_size, 0, f"empty file: {path}")

    def test_generates_all_four_plots_for_normal_input(self) -> None:
        df = self._sample_group_df()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self._assert_non_empty(plot_success_rate(df, out))
            self._assert_non_empty(plot_risk_distribution(df, out))
            self._assert_non_empty(plot_uncertainty_overview(df, out))
            self._assert_non_empty(plot_risk_heatmap(df, out))

    def test_generates_all_four_plots_for_empty_input(self) -> None:
        df = self._empty_group_df()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self._assert_non_empty(plot_success_rate(df, out))
            self._assert_non_empty(plot_risk_distribution(df, out))
            self._assert_non_empty(plot_uncertainty_overview(df, out))
            self._assert_non_empty(plot_risk_heatmap(df, out))

    def test_group_labels_use_source_file(self) -> None:
        df = self._sample_group_df()
        labeled = _group_label_df(df)
        self.assertEqual(
            labeled["group_label"].tolist(),
            ["jailbreak:file_a.jsonl", "defense_input_layer:file_b.jsonl"],
        )


if __name__ == "__main__":
    unittest.main()
