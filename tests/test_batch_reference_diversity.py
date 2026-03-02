import types
import unittest

from redteam_llm.surrogate_model import SurrogateConfig, SurrogateModel


class BatchReferenceDiversityTest(unittest.TestCase):
    def test_batch_can_prefer_different_reference_samples_per_prompt(self):
        cfg = SurrogateConfig(
            model_type="openai_compatible",
            base_url="http://localhost:9999",
            num_variants=1,
            top_k=2,
            batch_unique_references=True,
        )
        model = SurrogateModel("Attack_Dataset/JailBench_seed.csv", cfg)
        model.dataset = [
            {"id": "a", "prompt": "alpha shared token"},
            {"id": "b", "prompt": "beta shared token"},
            {"id": "c", "prompt": "gamma shared token"},
            {"id": "d", "prompt": "delta shared token"},
        ]

        captured_refs = []

        async def fake_generate_single(self, original_prompt, reference_prompts):
            captured_refs.append([item["id"] for item in reference_prompts])
            return "ok"

        model._generate_single = types.MethodType(fake_generate_single, model)

        shared_state = set()
        model.generate_sync("shared token", num_variants=1, top_k=2, batch_reference_state=shared_state)
        model.generate_sync("shared token", num_variants=1, top_k=2, batch_reference_state=shared_state)

        self.assertEqual(captured_refs[0], ["a", "b"])
        self.assertEqual(captured_refs[1], ["c", "d"])


if __name__ == "__main__":
    unittest.main()
