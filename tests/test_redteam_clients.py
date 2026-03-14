import unittest

from Redteam.redteam_llm.clients import ClientConfig


class RedteamClientConfigTest(unittest.TestCase):
    def test_client_config_uses_safe_default_timeout(self):
        cfg = ClientConfig(timeout_s=0)
        self.assertGreaterEqual(cfg.timeout_s, 1.0)


if __name__ == "__main__":
    unittest.main()
