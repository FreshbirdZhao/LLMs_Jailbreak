import unittest
from unittest.mock import patch

from Jailbreak.jailbreak_tools.single_jail.model_tester import MultiTurnModelTester


class MultiTurnModelTesterTest(unittest.TestCase):
    def test_build_openai_payload_uses_chat_messages(self):
        tester = MultiTurnModelTester.__new__(MultiTurnModelTester)

        payload = tester._build_openai_payload(
            {"model": "demo"},
            [{"role": "user", "content": "hello"}],
        )

        self.assertEqual(payload["model"], "demo")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "hello"}])

    def test_get_model_returns_named_model(self):
        tester = MultiTurnModelTester.__new__(MultiTurnModelTester)
        tester.models_config_path = "models.yaml"

        with patch(
            "Jailbreak.jailbreak_tools.single_jail.model_tester.resolve_model",
            return_value={
                "name": "planner",
                "model": "planner-target",
                "base_url": "http://localhost:11434",
                "type": "ollama",
            },
        ):
            model = tester.get_model("planner")

        self.assertEqual(model["name"], "planner")
        self.assertEqual(model["model"], "planner-target")

    def test_get_model_returns_none_for_incomplete_config(self):
        tester = MultiTurnModelTester.__new__(MultiTurnModelTester)
        tester.models_config_path = "models.yaml"

        with patch(
            "Jailbreak.jailbreak_tools.single_jail.model_tester.resolve_model",
            return_value={
                "name": "planner",
                "model": "",
                "base_url": "http://localhost:11434",
                "type": "ollama",
            },
        ):
            model = tester.get_model("planner")

        self.assertIsNone(model)


if __name__ == "__main__":
    unittest.main()
