from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path


class MultiTurnResultWriter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self.path.open("a", encoding="utf-8")
        self._lock = asyncio.Lock()

    def write(self, record: dict) -> None:
        row = dict(record)
        row.setdefault("timestamp", datetime.now().isoformat())
        self._fp.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._fp.flush()

    def fsync(self) -> None:
        self._fp.flush()
        os.fsync(self._fp.fileno())

    async def write_async(self, record: dict) -> None:
        async with self._lock:
            self.write(record)

    async def fsync_async(self) -> None:
        async with self._lock:
            self.fsync()

    @staticmethod
    def load_completed_pairs(path: str | Path) -> set[tuple[str, str]]:
        output_path = Path(path)
        pairs: set[tuple[str, str]] = set()
        if not output_path.exists():
            return pairs

        with output_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                model_name = str(row.get("model_name") or "").strip()
                test_id = str(row.get("test_id") or "").strip()
                if model_name and test_id:
                    pairs.add((model_name, test_id))
        return pairs

    def close(self) -> None:
        if self._fp:
            self._fp.close()
