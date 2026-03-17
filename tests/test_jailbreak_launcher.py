from pathlib import Path
import unittest


class JailbreakLauncherTest(unittest.TestCase):
    def test_launcher_targets_new_multi_turn_entrypoints(self):
        path = Path("/home/jellyz/Experiment/Jelly_Z/bin/jailbreak")
        content = path.read_text(encoding="utf-8")

        self.assertIn('ATTACK_SCRIPT="$TOOLS_DIR/single_jail/single_jail.py"', content)
        self.assertIn('ATTACK_SCRIPT="$TOOLS_DIR/multi_jail/multi_jail.py"', content)
        self.assertIn("--datasets", content)
        self.assertIn(
            'DEFENSE_ARGS+=(--enable-defense --defense-config "$DEFENSE_CFG" --defense-archive-format "jsonl")',
            content,
        )
        self.assertNotIn('ATTACK_SCRIPT="$TOOLS_DIR/single_jail.py"', content)
        self.assertNotIn('ATTACK_SCRIPT="$TOOLS_DIR/multi.py"', content)

    def test_multi_step_mode_requires_planner_model_selection(self):
        path = Path("/home/jellyz/Experiment/Jelly_Z/bin/jailbreak")
        content = path.read_text(encoding="utf-8")

        self.assertIn("请选择辅助模型：", content)
        self.assertIn('echo "✔ 已选择辅助模型：$PLANNER_MODEL_NAME"', content)
        self.assertIn('--planner-model "$PLANNER_MODEL_NAME"', content)
        self.assertIn(
            'ensure_ollama_for_base_url "$PLANNER_MODEL_BASE_URL" "jailbreak-planner"',
            content,
        )

    def test_multi_step_mode_requires_judge_model_selection(self):
        path = Path("/home/jellyz/Experiment/Jelly_Z/bin/jailbreak")
        content = path.read_text(encoding="utf-8")

        self.assertIn("请选择判定模型：", content)
        self.assertIn('echo "✔ 已选择判定模型：$JUDGE_MODEL_NAME"', content)
        self.assertIn('--judge-model "$JUDGE_MODEL_NAME"', content)
        self.assertIn(
            'ensure_ollama_for_base_url "$JUDGE_MODEL_BASE_URL" "jailbreak-judge"',
            content,
        )


if __name__ == "__main__":
    unittest.main()
