import unittest

from Defense.defense_mode.engine import DefenseEngine
from Defense.defense_mode.types import DefenseAction, DefenseDecision


class _Module:
    def __init__(self, name, action=DefenseAction.ALLOW):
        self.name = name
        self.action = action
        self.calls = []

    def process(self, context):
        self.calls.append(self.name)
        return DefenseDecision(action=self.action, risk_level=0)


class DefenseEngineTest(unittest.TestCase):
    def test_pre_and_post_hooks_run_in_expected_order(self):
        input_module = _Module("input")
        interaction_module = _Module("interaction")
        output_module = _Module("output")
        engine = DefenseEngine(input_module, interaction_module, output_module)
        ctx = engine.build_context_from_case({"id": "1", "prompt": "p"}, model_name="m")
        engine.apply_pre_call_defense(ctx)
        engine.apply_post_call_defense(ctx, "resp")
        self.assertEqual(ctx.decision_history[0]["layer"], "input")
        self.assertEqual(ctx.decision_history[1]["layer"], "interaction_pre")
        self.assertEqual(ctx.decision_history[2]["layer"], "output")
        self.assertEqual(ctx.decision_history[3]["layer"], "interaction_post")


if __name__ == "__main__":
    unittest.main()

