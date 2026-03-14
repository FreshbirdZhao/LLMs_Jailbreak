from pathlib import Path
import unittest

from Jailbreak.jailbreak_tools.multi_jail.runtime import ResumeTracker
from Jailbreak.jailbreak_tools.multi_jail.runner import MultiTurnCaseRunner
from Jailbreak.jailbreak_tools.single_jail import MultiTurnModelTester


class JailbreakRuntimeTest(unittest.TestCase):
    def test_runner_clamps_max_rounds_to_one(self):
        runner = MultiTurnCaseRunner(model_caller=None, max_rounds=0)
        self.assertEqual(runner.max_rounds, 1)


class JailbreakRetryPolicyTest(unittest.TestCase):
    def test_package_exports_multi_turn_model_tester(self):
        self.assertIs(MultiTurnModelTester, MultiTurnModelTester)


class JailbreakMigrationTest(unittest.TestCase):
    def test_legacy_flat_scripts_are_removed(self):
        root = Path(__file__).resolve().parents[1] / "Jailbreak" / "jailbreak_tools"
        self.assertFalse((root / "single_jail.py").exists())
        self.assertFalse((root / "multi.py").exists())


class ResumeTrackerTest(unittest.TestCase):
    def test_resume_tracker_skips_completed_pair(self):
        tracker = ResumeTracker(total=2, completed_pairs={("demo", "jb_1")})

        self.assertTrue(tracker.should_skip("demo", "jb_1"))
        self.assertFalse(tracker.should_skip("demo", "jb_2"))


if __name__ == "__main__":
    unittest.main()
