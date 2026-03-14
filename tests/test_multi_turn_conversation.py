import unittest

from Jailbreak.jailbreak_tools.single_jail.conversation import ConversationState


class ConversationStateTest(unittest.TestCase):
    def test_conversation_appends_user_and_assistant_messages(self):
        convo = ConversationState(
            case_id="jb_1",
            case_name="case",
            original_prompt="hello",
            max_rounds=6,
        )

        convo.add_user_message("hello")
        convo.add_assistant_message("refused")

        self.assertEqual(convo.current_round, 1)
        self.assertEqual(
            convo.messages,
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "refused"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
