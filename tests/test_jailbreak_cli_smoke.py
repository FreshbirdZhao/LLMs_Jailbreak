from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Analyze.cli import run_cli


class TestJailbreakCliSmoke(unittest.TestCase):
    def test_cli_generates_csv_and_four_figures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            input_dir.mkdir(parents=True, exist_ok=True)
            sample_jsonl = input_dir / "sample.jsonl"

            rows = [
                {
                    "model_name": "qwen2",
                    "attack_type": "direct",
                    "category": "harmful",
                    "prompt": "how to do x",
                    "response": "第一步 搭建 环境",
                },
                {
                    "model_name": "qwen2",
                    "attack_type": "direct",
                    "category": "harmful",
                    "prompt": "how to do y",
                    "response": "I cannot assist with illegal activity.",
                },
                {
                    "model_name": "qwen2",
                    "attack_type": "obfuscated",
                    "category": "harmful",
                    "prompt": "how to do z",
                    "response": "Use TOR proxy in steps.",
                },
            ]
            with sample_jsonl.open("w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            output_root = root / "out"
            code = run_cli(
                [
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_root),
                    "--judge-mode",
                    "keyword",
                    "--no-show-progress",
                ]
            )
            self.assertEqual(code, 0)

            mode_dir = output_root / "keyword"
            self.assertTrue((mode_dir / "records.csv").exists())
            self.assertTrue((mode_dir / "group_metrics.csv").exists())

            fig_dir = mode_dir / "figures"
            expected = [
                "success_rate.png",
                "risk_distribution.png",
                "uncertainty_overview.png",
                "risk_heatmap.png",
            ]
            for name in expected:
                p = fig_dir / name
                self.assertTrue(p.exists(), f"missing figure: {p}")
                self.assertGreater(p.stat().st_size, 0, f"empty figure: {p}")

    def test_cli_accepts_output_run_subdir_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            input_dir.mkdir(parents=True, exist_ok=True)
            sample_jsonl = input_dir / "sample.jsonl"
            sample_jsonl.write_text(
                json.dumps(
                    {
                        "model_name": "qwen2",
                        "attack_type": "direct",
                        "category": "harmful",
                        "prompt": "x",
                        "response": "I cannot help with that.",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            output_root = root / "out"
            code = run_cli(
                [
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_root),
                    "--output-run-subdir",
                    "all_files",
                    "--judge-mode",
                    "keyword",
                    "--no-show-progress",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue((output_root / "keyword" / "all_files" / "records.csv").exists())

    def test_cli_writes_source_manifest_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_code = f"test_run_{root.name[-6:]}"
            registry_path = (
                Path("/home/jellyz/Experiment/Results")
                / "directory"
                / f"{run_code}.json"
            )
            input_dir = root / "input"
            input_dir.mkdir(parents=True, exist_ok=True)
            (input_dir / "sample.jsonl").write_text(
                json.dumps(
                    {
                        "model_name": "qwen2",
                        "attack_type": "direct",
                        "category": "harmful",
                        "prompt": "x",
                        "response": "I cannot help with that.",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            manifest = root / "sources.tsv"
            manifest.write_text(
                "jailbreak:sample.jsonl\t/home/demo/jailbreak_results/sample.jsonl\t001_sample.jsonl\n",
                encoding="utf-8",
            )

            output_root = root / "out"
            code = run_cli(
                [
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_root),
                    "--output-run-subdir",
                    run_code,
                    "--judge-mode",
                    "keyword",
                    "--analysis-code",
                    run_code,
                    "--source-manifest-file",
                    str(manifest),
                    "--no-show-progress",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue((output_root / "keyword" / run_code / "input_sources.json").exists())
            self.assertTrue(registry_path.exists())
            if registry_path.exists():
                registry_path.unlink()


if __name__ == "__main__":
    unittest.main()
