import unittest

from results_analyze.jailbreak_metrics.plotting import _pick_best_chinese_font


class PlottingFontConfigTest(unittest.TestCase):
    def test_pick_first_available_preferred_font(self):
        installed = {"Arial", "Noto Sans CJK SC", "DejaVu Sans"}
        picked = _pick_best_chinese_font(installed)
        self.assertEqual(picked, "Noto Sans CJK SC")

    def test_no_candidate_returns_none(self):
        installed = {"Arial", "DejaVu Sans"}
        picked = _pick_best_chinese_font(installed)
        self.assertIsNone(picked)


if __name__ == "__main__":
    unittest.main()
