import unittest

from Jailbreak.jailbreak_tools.single_jail.judgers import NonRefusalJudge


class NonRefusalJudgeTest(unittest.TestCase):
    def test_marks_refusal_response(self):
        judge = NonRefusalJudge()

        result = judge.judge("I cannot assist with that.")

        self.assertEqual(result.status, "refused")

    def test_marks_regular_answer_as_success(self):
        judge = NonRefusalJudge()

        result = judge.judge("Here is a detailed answer.")

        self.assertEqual(result.status, "success")


if __name__ == "__main__":
    unittest.main()
