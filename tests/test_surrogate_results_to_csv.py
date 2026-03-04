import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from results_analyze.format_conversion.surrogate_to_csv import _clean_prompt, convert_surrogate_json_to_csv


class SurrogateResultsToCsvTest(unittest.TestCase):
    def test_clean_prompt_skips_failure_with_reason(self):
        self.assertEqual(_clean_prompt("生成失败（原因: mock network down）"), "")

    def test_default_output_name_uses_surrogate_yymmdd(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "input.json"
            input_path.write_text(
                '{"original_prompt":"o","generated_prompt":"p","model":"m","timestamp":"t"}',
                encoding="utf-8",
            )

            output_path = Path(convert_surrogate_json_to_csv(str(input_path), str(tmp_path)))
            expected_name = f"surrogate_{datetime.now().strftime('%y%m%d')}.csv"
            self.assertEqual(output_path.name, expected_name)


if __name__ == "__main__":
    unittest.main()
