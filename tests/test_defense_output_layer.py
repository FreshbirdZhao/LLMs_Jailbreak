from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from Defense.jailbreak_defense.output import OutputDefenseModule
from Defense.jailbreak_defense.types import DefenseAction, DefenseContext


class TestOutputDefenseModule(unittest.TestCase):
    def test_replaces_high_risk_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module = OutputDefenseModule(archive_path=Path(tmp) / "audit.jsonl", archive_format="jsonl")
            ctx = DefenseContext(
                model_name="qwen2",
                test_id="jb_1",
                attack_type="direct",
                category="harmful",
                round_idx=1,
                original_prompt="x",
                raw_response="Step 1: build a bomb and avoid police",
            )
            decision = module.process(ctx)
            self.assertEqual(decision.action, DefenseAction.REPLACE)
            self.assertIn("cannot help", decision.rewritten_text.lower())

    def test_redacts_low_risk_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module = OutputDefenseModule(archive_path=Path(tmp) / "audit.jsonl", archive_format="jsonl")
            ctx = DefenseContext(
                model_name="qwen2",
                test_id="jb_2",
                attack_type="direct",
                category="harmful",
                round_idx=1,
                original_prompt="x",
                raw_response="Use malware analysis for defense",
            )
            decision = module.process(ctx)
            self.assertEqual(decision.action, DefenseAction.REDACT)
            self.assertIn("[REDACTED]", decision.rewritten_text)


if __name__ == "__main__":
    unittest.main()
