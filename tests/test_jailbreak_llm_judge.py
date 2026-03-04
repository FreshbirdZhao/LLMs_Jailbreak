import unittest

from results_analyze.jailbreak_metrics.judges.llm_judge import LLMJudge
from results_analyze.jailbreak_metrics.llm_clients import build_llm_client


class DummyClient:
    def __init__(self, payload: str):
        self.payload = payload

    def complete(self, prompt: str) -> str:
        return self.payload


class FailingClient:
    provider_name = "ollama"

    def complete(self, prompt: str) -> str:
        raise RuntimeError("connection failed")


class JailbreakLLMJudgeTest(unittest.TestCase):
    def test_provider_selection(self):
        ollama_client = build_llm_client({"provider": "ollama", "model": "qwen2:latest"})
        external_client = build_llm_client({"provider": "external", "model": "gpt-4o-mini"})
        self.assertEqual(ollama_client.provider_name, "ollama")
        self.assertEqual(external_client.provider_name, "external")

    def test_parse_json_success(self):
        judge = LLMJudge(client=DummyClient('{"is_jailbreak":"yes","risk_level":4,"evidence_spans":["abc"]}'))
        out = judge.judge("sample response")
        self.assertEqual(out.is_jailbreak, "yes")
        self.assertEqual(out.risk_level, 4)
        self.assertEqual(out.evidence_spans, ["abc"])

    def test_parse_failure_fallback(self):
        judge = LLMJudge(client=DummyClient('not-json'))
        out = judge.judge("sample response")
        self.assertEqual(out.is_jailbreak, "uncertain")
        self.assertIn("llm_parse_failed", out.reasoning_tags)

    def test_request_failure_raises(self):
        judge = LLMJudge(client=FailingClient())
        with self.assertRaises(RuntimeError) as ctx:
            judge.judge("sample response")
        self.assertIn("LLM request failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
