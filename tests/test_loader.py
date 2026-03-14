import unittest

from Jailbreak.jailbreak_tools.loader import Loader


class LoaderTest(unittest.TestCase):
    def test_normalize_case_prefers_existing_ids_and_prompt_aliases(self):
        loader = Loader()
        case = loader._normalize_case(
            {"test_id": "42", "query": "hello", "type": "cat", "method": "attack"},
            fallback_id="9",
        )
        self.assertEqual(case["id"], "jb_42")
        self.assertEqual(case["prompt"], "hello")
        self.assertEqual(case["category"], "cat")
        self.assertEqual(case["attack_type"], "attack")


if __name__ == "__main__":
    unittest.main()

