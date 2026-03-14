from __future__ import annotations

import asyncio
import os
import sys


def render_progress_line(completed: int, total: int, status: str, width: int = 20) -> str:
    total = max(1, int(total))
    completed = max(0, min(int(completed), total))
    width = max(1, int(width))
    ratio = completed / total
    filled = int(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{completed}/{total}] {bar} {ratio * 100:.1f}% | {status}"


class ResumeTracker:
    def __init__(self, total: int, completed_pairs: set[tuple[str, str]] | None = None):
        self.total = max(0, int(total))
        self.completed_pairs = completed_pairs or set()
        self.completed = 0
        self.stats = {
            "skipped": 0,
            "success": 0,
            "blocked": 0,
            "refused": 0,
            "error": 0,
        }

    def should_skip(self, model_name: str, test_id: str) -> bool:
        return (model_name, test_id) in self.completed_pairs

    def record(self, status: str) -> None:
        self.completed += 1
        if status in self.stats:
            self.stats[status] += 1

    def progress_line(self, status: str) -> str:
        return render_progress_line(self.completed, self.total, status)


async def run_task_queue(tasks: list[dict], concurrency: int, tracker: ResumeTracker, worker_fn) -> None:
    queue: asyncio.Queue = asyncio.Queue()
    concurrency = max(1, int(concurrency))

    for task in tasks:
        model_name = str(task.get("model_name") or "").strip()
        test_id = str(task.get("test_id") or "").strip()
        if tracker.should_skip(model_name, test_id):
            tracker.record("skipped")
            continue
        await queue.put(task)

    async def _worker() -> None:
        while True:
            try:
                task = await asyncio.wait_for(queue.get(), timeout=0.05)
            except asyncio.TimeoutError:
                if queue.empty():
                    return
                continue
            try:
                status = await worker_fn(task)
                tracker.record(status)
            finally:
                queue.task_done()

    workers = [asyncio.create_task(_worker()) for _ in range(concurrency)]
    await queue.join()
    await asyncio.gather(*workers, return_exceptions=True)


async def autosave_loop(writer, interval: int, stop_event: asyncio.Event) -> None:
    if interval <= 0:
        return
    while not stop_event.is_set():
        await asyncio.sleep(interval)
        await writer.fsync_async()


def emit_progress(line: str) -> None:
    if sys.stdout.isatty():
        print(f"\r{line}", end="", flush=True)
    else:
        print(line, flush=True)


def finish_progress() -> None:
    if sys.stdout.isatty():
        print()
