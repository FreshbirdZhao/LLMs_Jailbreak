from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ArchiveStore:
    def __init__(self, path: str | Path, fmt: str = "jsonl") -> None:
        self.path = Path(path)
        self.fmt = fmt
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.fmt == "sqlite":
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        conn = sqlite3.connect(self.path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS defense_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT,
                    test_id TEXT,
                    layer TEXT,
                    action TEXT,
                    risk_level INTEGER,
                    reasons TEXT,
                    payload TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def append(self, record: dict[str, Any]) -> None:
        if self.fmt == "sqlite":
            conn = sqlite3.connect(self.path)
            try:
                conn.execute(
                    """
                    INSERT INTO defense_audit (model_name, test_id, layer, action, risk_level, reasons, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.get("model_name", ""),
                        record.get("test_id", ""),
                        record.get("layer", ""),
                        record.get("action", ""),
                        int(record.get("risk_level", 0)),
                        json.dumps(record.get("reasons", []), ensure_ascii=False),
                        json.dumps(record, ensure_ascii=False),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            return

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
