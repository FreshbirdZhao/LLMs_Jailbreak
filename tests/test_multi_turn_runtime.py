import unittest
import asyncio

from Jailbreak.jailbreak_tools.multi_jail.runtime import ResumeTracker, render_progress_line, run_task_queue


class MultiTurnRuntimeTest(unittest.TestCase):
    def test_render_progress_line_uses_compact_format(self):
        line = render_progress_line(completed=12, total=80, status="success", width=20)

        self.assertIn("[12/80]", line)
        self.assertIn("15.0%", line)
        self.assertTrue(line.endswith("| success"))

    def test_resume_tracker_records_skipped_completion(self):
        tracker = ResumeTracker(total=2, completed_pairs={("demo", "jb_1")})
        tracker.record("skipped")
        self.assertEqual(tracker.completed, 1)
        self.assertEqual(tracker.stats["skipped"], 1)

    def test_run_task_queue_skips_completed_pairs_before_queueing(self):
        async def _run():
            calls = []

            async def worker(item):
                calls.append(item["test_id"])
                return "success"

            tracker = ResumeTracker(total=2, completed_pairs={("demo", "jb_1")})
            tasks = [
                {"model_name": "demo", "test_id": "jb_1"},
                {"model_name": "demo", "test_id": "jb_2"},
            ]
            await run_task_queue(tasks=tasks, concurrency=2, tracker=tracker, worker_fn=worker)
            return calls, tracker

        calls, tracker = asyncio.run(_run())

        self.assertEqual(calls, ["jb_2"])
        self.assertEqual(tracker.completed, 2)
        self.assertEqual(tracker.stats["skipped"], 1)
        self.assertEqual(tracker.stats["success"], 1)


if __name__ == "__main__":
    unittest.main()
