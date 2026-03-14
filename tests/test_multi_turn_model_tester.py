import unittest

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


if __name__ == "__main__":
    unittest.main()
