import json
import tempfile
import unittest
from pathlib import Path

from Jailbreak.jailbreak_tools.multi_jail.result_writer import MultiTurnResultWriter


def sample_record() -> dict:
    return {
        "model_name": "qwen2:latest",
        "test_id": "jb_1",
        "test_name": "case",
        "category": "cat",
        "attack_type": "attack",
        "prompt": "original prompt",
        "response": "final response",
        "http_status": 200,
        "elapsed_time": 12.3,
        "final_status": "refused",
        "success_round": None,
        "rounds_used": 2,
        "judge_mode": "layered_llm",
        "judge_model_name": "judge",
        "judge_final_reason": "reason",
        "judge_final_confidence": "high",
        "max_rounds": 6,
        "planner_model_name": "planner",
        "initial_attack_plan": {"plan_source": "initial"},
        "active_plan_versions": [{"plan_source": "initial"}],
        "replan_events": [{"trigger_round": 2}],
        "conversation": [
            {
                "round": 1,
                "plan_round_idx": 1,
                "plan_version": 1,
                "plan_goal": "goal 1",
                "plan_strategy": "strategy 1",
                "user_prompt": "user prompt 1",
                "assistant_response": "assistant response 1",
                "raw_assistant_response": "raw assistant response 1",
                "elapsed_time": 1.0,
                "judge_stage": "llm",
                "judge_status": "refused",
                "judge_reason": "reason 1",
                "judge_feedback": {"status": "refused"},
                "judge_model_name": "judge",
                "judge_confidence": "medium",
                "defense_action": "allow",
                "defense_risk_level": 0,
                "defense_reasons": [],
                "defense_prompt": "sanitized prompt",
                "followup_prompt": "followup 1",
                "followup_strategy": "adaptive_planner",
                "followup_generator_model": "planner",
                "followup_generation_error": "",
            }
        ],
        "defense_enabled": False,
        "defense_blocked": False,
        "defense_final_action": "allow",
        "defense_final_risk_level": 0,
        "defense_final_reasons": [],
    }


class MultiTurnResultWriterTest(unittest.TestCase):
    def test_summary_output_keeps_only_user_facing_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            writer = MultiTurnResultWriter(output_path)
            try:
                writer.write(sample_record())
            finally:
                writer.close()

            row = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(row["model_name"], "qwen2:latest")
        self.assertEqual(row["prompt"], "original prompt")
        self.assertEqual(row["conversation"][0]["input_prompt"], "user prompt 1")
        self.assertEqual(row["conversation"][0]["output_response"], "assistant response 1")
        self.assertNotIn("initial_attack_plan", row)
        self.assertNotIn("active_plan_versions", row)
        self.assertNotIn("replan_events", row)
        self.assertNotIn("response", row)
        self.assertNotIn("raw_assistant_response", row["conversation"][0])
        self.assertNotIn("judge_feedback", row["conversation"][0])
        self.assertNotIn("plan_goal", row["conversation"][0])

    def test_writer_persists_full_debug_record_to_debug_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            debug_root = Path(tmpdir) / "debug_store"
            writer = MultiTurnResultWriter(output_path, debug_root=debug_root)
            try:
                writer.write(sample_record())
            finally:
                writer.close()

            debug_files = list(debug_root.rglob("*.json"))
            self.assertEqual(len(debug_files), 1)
            debug_row = json.loads(debug_files[0].read_text(encoding="utf-8"))

        self.assertIn("initial_attack_plan", debug_row)
        self.assertIn("active_plan_versions", debug_row)
        self.assertIn("replan_events", debug_row)
        self.assertIn("raw_assistant_response", debug_row["conversation"][0])


if __name__ == "__main__":
    unittest.main()
