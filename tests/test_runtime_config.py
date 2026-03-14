import unittest

from common.runtime import RetryPolicy


class RetryPolicyTest(unittest.TestCase):
    def test_retry_policy_clamps_invalid_values(self):
        policy = RetryPolicy(timeout=0, max_retries=-2, retry_backoff=-1)
        self.assertEqual(policy.timeout, 1)
        self.assertEqual(policy.max_retries, 0)
        self.assertEqual(policy.retry_backoff, 0.0)


if __name__ == "__main__":
    unittest.main()
