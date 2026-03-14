import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from Jailbreak.jailbreak_tools.multi_jail.result_writer import MultiTurnResultWriter


class MultiTurnResultWriterTest(unittest.TestCase):
    def test_writer_persists_response_and_conversation(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.jsonl"
            writer = MultiTurnResultWriter(path)
            writer.write(
                {
                    "model_name": "demo",
                    "test_id": "jb_1",
                    "test_name": "case",
                    "category": "c",
                    "attack_type": "a",
                    "prompt": "attack",
                    "response": "answer",
                    "http_status": 200,
                    "elapsed_time": 0.2,
                    "final_status": "success",
                    "success_round": 2,
                    "rounds_used": 2,
                    "judge_mode": "non_refusal",
                    "max_rounds": 6,
                    "conversation": [{"round": 1}],
                }
            )
            writer.close()

            data = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(data["response"], "answer")
            self.assertEqual(data["conversation"], [{"round": 1}])

    def test_writer_loads_completed_pairs_from_existing_jsonl(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.jsonl"
            path.write_text(
                json.dumps({"model_name": "demo", "test_id": "jb_1"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            pairs = MultiTurnResultWriter.load_completed_pairs(path)

            self.assertEqual(pairs, {("demo", "jb_1")})


if __name__ == "__main__":
    unittest.main()
