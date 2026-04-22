from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from Jailbreak.jailbreak_tools.multi_jail.result_writer import MultiTurnResultWriter, OrderedResultWriter
from Jailbreak.jailbreak_tools.multi_jail.runtime import ResumeTracker, run_task_queue
from Jailbreak.jailbreak_tools.single_jail.single_jail import build_parser


def build_record(index: int) -> dict:
    return {
        "model_name": "demo-model",
        "test_id": f"test-{index}",
        "test_name": f"case-{index}",
        "category": "demo",
        "attack_type": "demo",
        "attack_dimension": "",
        "attack_method": "",
        "source_prompt": "",
        "source_file": "",
        "prompt": f"prompt-{index}",
        "response": f"response-{index}",
        "http_status": 200,
        "elapsed_time": 0.01,
        "final_status": "success",
        "success_round": 1,
        "rounds_used": 1,
        "judge_model_name": "",
        "judge_final_reason": "ok",
        "judge_final_confidence": "",
        "planner_model_name": "",
        "conversation": [],
    }


class SingleJailOrderingTest(unittest.IsolatedAsyncioTestCase):
    def test_default_concurrency_is_eight(self) -> None:
        args = build_parser().parse_args(
            ["--models", "demo-model", "--dataset", "demo.jsonl", "--output-dir", "out"]
        )
        self.assertEqual(args.concurrency, 8)

    async def test_results_are_flushed_in_batches_of_twelve(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            writer = MultiTurnResultWriter(output_path)
            ordered_writer = OrderedResultWriter(writer)
            try:
                for index in range(11):
                    await ordered_writer.write_async(index, build_record(index))

                self.assertEqual(output_path.read_text(encoding="utf-8"), "")

                await ordered_writer.write_async(11, build_record(11))

                rows = [
                    json.loads(line)
                    for line in output_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                self.assertEqual(len(rows), 12)
                self.assertEqual(rows[0]["test_id"], "test-0")
                self.assertEqual(rows[-1]["test_id"], "test-11")
            finally:
                writer.close()

    async def test_results_keep_dataset_order_with_concurrency(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            writer = MultiTurnResultWriter(output_path)
            ordered_writer = OrderedResultWriter(writer)
            tracker = ResumeTracker(total=3)
            tasks = [
                {"index": 0, "delay": 0.03, "model_name": "demo-model", "test_id": "test-0"},
                {"index": 1, "delay": 0.01, "model_name": "demo-model", "test_id": "test-1"},
                {"index": 2, "delay": 0.0, "model_name": "demo-model", "test_id": "test-2"},
            ]

            async def worker_fn(task: dict) -> str:
                await asyncio.sleep(task["delay"])
                await ordered_writer.write_async(task["index"], build_record(task["index"]))
                return "success"

            try:
                await run_task_queue(tasks=tasks, concurrency=3, tracker=tracker, worker_fn=worker_fn)
            finally:
                await writer.fsync_async()
                writer.close()

            rows = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            self.assertEqual(
                [row["test_id"] for row in rows],
                ["test-0", "test-1", "test-2"],
            )


if __name__ == "__main__":
    unittest.main()
