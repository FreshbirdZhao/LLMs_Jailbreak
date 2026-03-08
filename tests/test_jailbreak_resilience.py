from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Analyze.llm_clients import OllamaClient
from Analyze.pipeline import evaluate_records
from Analyze.schema import JudgeDecision


class _PassThroughPolicyJudge:
    def judge(self, base_decision: JudgeDecision, response_text: str) -> JudgeDecision:
        return base_decision


class _CrashOnNthJudge:
    def __init__(self, n: int) -> None:
        self.n = n
        self.calls = 0

    def judge(self, response_text: str) -> JudgeDecision:
        self.calls += 1
        if self.calls == self.n:
            raise RuntimeError("simulated ollama failure")
        return JudgeDecision(is_jailbreak="no", risk_level=0, judge_source="test")


class _CountingJudge:
    def __init__(self) -> None:
        self.calls = 0

    def judge(self, response_text: str) -> JudgeDecision:
        self.calls += 1
        return JudgeDecision(is_jailbreak="no", risk_level=0, judge_source="test")


class _DummyHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class TestJailbreakResilience(unittest.TestCase):
    def test_pipeline_resume_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "out"
            input_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            sample_path = input_dir / "sample.jsonl"
            rows = [
                {"model_name": "m", "attack_type": "a", "response": "r1"},
                {"model_name": "m", "attack_type": "a", "response": "r2"},
                {"model_name": "m", "attack_type": "a", "response": "r3"},
            ]
            with sample_path.open("w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            with self.assertRaises(RuntimeError):
                evaluate_records(
                    input_dir=input_dir,
                    base_judge=_CrashOnNthJudge(n=2),
                    policy_judge=_PassThroughPolicyJudge(),
                    checkpoint_dir=output_dir,
                    resume=True,
                )

            resumed = _CountingJudge()
            df = evaluate_records(
                input_dir=input_dir,
                base_judge=resumed,
                policy_judge=_PassThroughPolicyJudge(),
                checkpoint_dir=output_dir,
                resume=True,
            )
            self.assertEqual(len(df), 3)
            self.assertEqual(resumed.calls, 2)

    def test_ollama_client_retries_after_timeout(self) -> None:
        client = OllamaClient(
            model="qwen2:latest",
            base_url="http://127.0.0.1:11434",
            timeout=1,
            max_retries=2,
            retry_backoff=0,
        )

        with mock.patch.object(client, "_recover_service") as mock_recover:
            with mock.patch(
                "Analyze.llm_clients.request.urlopen",
                side_effect=[
                    TimeoutError("timed out"),
                    _DummyHTTPResponse({"response": '{"is_jailbreak":"no","risk_level":0,"evidence_spans":[]}'}),
                ],
            ) as mock_open:
                raw = client.complete("hello")

        self.assertIn("is_jailbreak", raw)
        self.assertEqual(mock_open.call_count, 2)
        mock_recover.assert_called_once()


if __name__ == "__main__":
    unittest.main()
