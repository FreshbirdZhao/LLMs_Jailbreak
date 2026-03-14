import unittest

from common.llm.config import normalize_provider_config


class SharedLLMConfigTest(unittest.TestCase):
    def test_normalize_provider_config_fills_provider_defaults(self):
        cfg = normalize_provider_config(
            {
                "provider": "external",
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
                "timeout": 20,
            }
        )
        self.assertEqual(cfg["provider"], "external")
        self.assertEqual(cfg["timeout"], 20)
        self.assertIn("max_retries", cfg)
        self.assertIn("retry_backoff", cfg)


if __name__ == "__main__":
    unittest.main()
