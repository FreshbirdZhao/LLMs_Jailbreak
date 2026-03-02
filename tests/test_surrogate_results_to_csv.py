import unittest

from results_analyze.surrogate_results_to_csv import _clean_prompt


class SurrogateResultsToCsvTest(unittest.TestCase):
    def test_clean_prompt_skips_failure_with_reason(self):
        self.assertEqual(_clean_prompt("生成失败（原因: mock network down）"), "")


if __name__ == "__main__":
    unittest.main()
