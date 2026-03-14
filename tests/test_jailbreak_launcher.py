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


if __name__ == "__main__":
    unittest.main()
