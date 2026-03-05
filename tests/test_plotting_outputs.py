import tempfile
import unittest
from pathlib import Path

import pandas as pd

from results_analyze.jailbreak_metrics.plotting import (
    plot_risk_distribution,
    plot_risk_heatmap,
    plot_success_rate,
    plot_uncertainty_overview,
)


class PlottingOutputsTest(unittest.TestCase):
    def test_plotting_generates_all_expected_files(self):
        group_df = pd.DataFrame(
            [
                {
                    "model_name": "m1",
                    "attack_type": "a1",
                    "total": 20,
                    "yes_count": 6,
                    "uncertain_count": 8,
                    "success_rate": 0.3,
                    "success_variance": 0.21,
                    "ci95_low": 0.14,
                    "ci95_high": 0.52,
                    "risk_0_ratio": 0.1,
                    "risk_1_ratio": 0.2,
                    "risk_2_ratio": 0.25,
                    "risk_3_ratio": 0.25,
                    "risk_4_ratio": 0.2,
                },
                {
                    "model_name": "m2",
                    "attack_type": "a2",
                    "total": 10,
                    "yes_count": 1,
                    "uncertain_count": 6,
                    "success_rate": 0.1,
                    "success_variance": 0.09,
                    "ci95_low": 0.02,
                    "ci95_high": 0.38,
                    "risk_0_ratio": 0.3,
                    "risk_1_ratio": 0.3,
                    "risk_2_ratio": 0.2,
                    "risk_3_ratio": 0.1,
                    "risk_4_ratio": 0.1,
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            files = [
                plot_success_rate(group_df, out),
                plot_risk_distribution(group_df, out),
                plot_uncertainty_overview(group_df, out),
                plot_risk_heatmap(group_df, out),
            ]
            for f in files:
                self.assertTrue(f.exists())
                self.assertGreater(f.stat().st_size, 0)

    def test_plotting_handles_empty_group_df(self):
        group_df = pd.DataFrame()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            files = [
                plot_success_rate(group_df, out),
                plot_risk_distribution(group_df, out),
                plot_uncertainty_overview(group_df, out),
                plot_risk_heatmap(group_df, out),
            ]
            for f in files:
                self.assertTrue(f.exists())
                self.assertGreater(f.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
