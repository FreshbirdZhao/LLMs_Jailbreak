import unittest

from redteam_llm.surrogate_model import SurrogateConfig, SurrogateModel


class _AlwaysFailClient:
    async def generate(self, prompt: str) -> str:
        raise RuntimeError("mock network down")


class _LowQualityClient:
    async def generate(self, prompt: str) -> str:
        return "完全无关内容"


class GenerationFailureReasonTest(unittest.TestCase):
    def test_returns_failure_text_with_exception_reason(self):
        cfg = SurrogateConfig(
            model_type="openai_compatible",
            base_url="http://localhost:9999",
            max_retries=1,
            failure_text="生成失败",
        )
        model = SurrogateModel("Attack_Dataset/JailBench_seed.csv", cfg)
        model.llm_client = _AlwaysFailClient()

        result = model.generate_sync("请帮我写一封请假邮件", num_variants=1, top_k=1)[0]

        self.assertIn("生成失败", result)
        self.assertIn("mock network down", result)

    def test_returns_failure_text_with_quality_gate_reason(self):
        cfg = SurrogateConfig(
            model_type="openai_compatible",
            base_url="http://localhost:9999",
            max_retries=0,
            quality_threshold=0.99,
            intent_threshold=0.99,
            anchor_threshold=0.99,
            failure_text="生成失败",
        )
        model = SurrogateModel("Attack_Dataset/JailBench_seed.csv", cfg)
        model.llm_client = _LowQualityClient()

        result = model.generate_sync("请帮我写一封请假邮件", num_variants=1, top_k=1)[0]

        self.assertIn("生成失败", result)
        self.assertIn("质量", result)


if __name__ == "__main__":
    unittest.main()
