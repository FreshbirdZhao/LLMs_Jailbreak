from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from Defense.reporting import export_defense_metrics


class DefenseReportingTest(unittest.TestCase):
    def test_export_defense_metrics_writes_expected_csvs(self) -> None:
        rows = [
            {
                "model_name": "demo-model",
                "test_id": "jb_1",
                "category": "demo",
                "attack_type": "demo",
                "attack_dimension": "cognitive_psychological",
                "source_file": "set_a.csv",
                "final_status": "blocked",
                "defense_enabled": True,
                "defense_blocked": True,
                "defense_final_action": "block",
                "defense_final_risk_level": 3,
                "defense_triggered_layers": ["input"],
                "defense_layers_enabled": ["input", "interaction", "output"],
                "defense_pre_action": "block",
                "defense_post_action": "allow",
                "defense_prompt_changed": False,
                "defense_response_changed": False,
                "defense_decision_history": [
                    {"layer": "input", "action": "block", "risk_level": 3, "reasons": ["input_high_risk"]},
                ],
            },
            {
                "model_name": "demo-model",
                "test_id": "jb_2",
                "category": "demo",
                "attack_type": "demo",
                "attack_dimension": "ascii_art",
                "source_file": "set_b.csv",
                "final_status": "success",
                "defense_enabled": True,
                "defense_blocked": False,
                "defense_final_action": "rewrite",
                "defense_final_risk_level": 2,
                "defense_triggered_layers": ["input"],
                "defense_layers_enabled": ["input"],
                "defense_pre_action": "rewrite",
                "defense_post_action": "allow",
                "defense_prompt_changed": True,
                "defense_response_changed": False,
                "defense_decision_history": [
                    {"layer": "input", "action": "rewrite", "risk_level": 2, "reasons": ["input_medium_risk"]},
                ],
            },
            {
                "model_name": "demo-model",
                "test_id": "jb_3",
                "category": "demo",
                "attack_type": "demo",
                "attack_dimension": "ascii_art",
                "source_file": "set_b.csv",
                "final_status": "refused",
                "defense_enabled": False,
                "defense_blocked": False,
                "defense_final_action": "allow",
                "defense_final_risk_level": 0,
                "defense_triggered_layers": [],
                "defense_layers_enabled": [],
                "defense_pre_action": "allow",
                "defense_post_action": "allow",
                "defense_prompt_changed": False,
                "defense_response_changed": False,
                "defense_decision_history": [],
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "results.jsonl"
            input_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            output_dir = Path(tmpdir) / "defense_metrics"

            outputs = export_defense_metrics(input_path, output_dir)

            expected_keys = {
                "defense_records",
                "defense_action_summary",
                "defense_group_metrics",
                "defense_layer_metrics",
            }
            self.assertEqual(set(outputs.keys()), expected_keys)
            for path in outputs.values():
                self.assertTrue(Path(path).exists())

            with outputs["defense_action_summary"].open("r", encoding="utf-8") as f:
                summary_rows = list(csv.DictReader(f))
            summary_by_action = {row["defense_final_action"]: row for row in summary_rows}
            self.assertEqual(summary_by_action["block"]["count"], "1")
            self.assertEqual(summary_by_action["rewrite"]["count"], "1")
            self.assertEqual(summary_by_action["allow"]["count"], "1")

            with outputs["defense_group_metrics"].open("r", encoding="utf-8") as f:
                group_rows = list(csv.DictReader(f))
            group_by_name = {row["analysis_group"]: row for row in group_rows}
            self.assertEqual(group_by_name["cognitive_psychological"]["blocked_count"], "1")
            self.assertEqual(group_by_name["ascii_art"]["rewrite_count"], "1")
            self.assertEqual(group_by_name["ascii_art"]["success_count"], "1")

            with outputs["defense_layer_metrics"].open("r", encoding="utf-8") as f:
                layer_rows = list(csv.DictReader(f))
            layer_keys = {(row["layer"], row["action"]) for row in layer_rows}
            self.assertIn(("input", "block"), layer_keys)
            self.assertIn(("input", "rewrite"), layer_keys)

    def test_reporting_cli_exports_metrics(self) -> None:
        rows = [
            {
                "model_name": "demo-model",
                "test_id": "jb_cli",
                "attack_dimension": "ascii_art",
                "final_status": "success",
                "defense_final_action": "rewrite",
                "defense_blocked": False,
                "defense_pre_action": "rewrite",
                "defense_post_action": "allow",
                "defense_prompt_changed": True,
                "defense_response_changed": False,
                "defense_decision_history": [
                    {"layer": "input", "action": "rewrite", "risk_level": 2},
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "results.jsonl"
            input_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            output_dir = Path(tmpdir) / "cli_metrics"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "Defense.reporting",
                    "--input",
                    str(input_path),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd="/home/jellyz/Experiment",
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((output_dir / "defense_records.csv").exists())
            self.assertTrue((output_dir / "defense_action_summary.csv").exists())
            self.assertTrue((output_dir / "defense_group_metrics.csv").exists())
            self.assertTrue((output_dir / "defense_layer_metrics.csv").exists())


if __name__ == "__main__":
    unittest.main()
