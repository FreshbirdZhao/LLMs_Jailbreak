import unittest

from Jailbreak.jailbreak_tools.single_jail import ModelTester


class JailbreakRuntimeTest(unittest.TestCase):
    def test_extract_round_idx_defaults_to_one(self):
        self.assertEqual(ModelTester._extract_round_idx({}), 1)


class JailbreakRetryPolicyTest(unittest.TestCase):
    def test_model_tester_keeps_retry_limit_non_negative(self):
        tester = ModelTester(
            "models.yaml",
            timeout=30,
            concurrency=1,
            retry_limit=-2,
            autosave_interval=0,
            resume=False,
            retry_backoff_base=1.0,
            retry_backoff_cap=5.0,
        )
        self.assertGreaterEqual(tester.retry_limit, 0)


if __name__ == "__main__":
    unittest.main()
