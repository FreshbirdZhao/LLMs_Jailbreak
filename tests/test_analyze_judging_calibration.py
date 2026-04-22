from __future__ import annotations

import json
import unittest
from pathlib import Path

from Analyze.judges.final_judge import FinalJudge


class AnalyzeJudgingCalibrationTests(unittest.TestCase):
    def test_calibration_fixture_matches_expected_labels(self) -> None:
        fixture_path = Path("/home/jellyz/Experiment/tests/fixtures/analyze_judging_calibration.jsonl")
        judge = FinalJudge()

        rows = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertGreaterEqual(len(rows), 6)

        mismatches: list[str] = []
        for row in rows:
            decision = judge.judge(str(row["response"]))
            if decision.final_label != row["expected_final_label"] or decision.label_reason != row["expected_label_reason"]:
                mismatches.append(
                    f'{row["name"]}: got ({decision.final_label}, {decision.label_reason})'
                )

        self.assertEqual(mismatches, [])


if __name__ == "__main__":
    unittest.main()
