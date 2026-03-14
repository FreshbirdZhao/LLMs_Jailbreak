import unittest

from Jailbreak.jailbreak_tools.multi_jail.prompt_strategy import DefaultFollowupStrategy


class DefaultFollowupStrategyTest(unittest.TestCase):
    def test_followup_uses_original_prompt_and_prior_response(self):
        strategy = DefaultFollowupStrategy()

        followup = strategy.build_next_prompt(
            original_prompt="Tell me how to do X",
            previous_response="I cannot help with that",
            round_idx=2,
        )

        self.assertIn("Tell me how to do X", followup)
        self.assertIn("I cannot help with that", followup)


if __name__ == "__main__":
    unittest.main()
