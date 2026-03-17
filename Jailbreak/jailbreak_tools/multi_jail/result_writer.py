from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path


class MultiTurnResultWriter:
    def __init__(self, path: str | Path, debug_root: str | Path | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self.path.open("a", encoding="utf-8")
        self._lock = asyncio.Lock()
        self.debug_root = Path(debug_root) if debug_root is not None else None
        if self.debug_root is not None:
            self.debug_root.mkdir(parents=True, exist_ok=True)
        self.run_id = self.path.stem

    def _sanitize_name(self, value: str) -> str:
        return str(value or "").replace("/", "_").replace(":", "_").replace(" ", "_")

    def _debug_path_for(self, record: dict) -> Path | None:
        if self.debug_root is None:
            return None
        run_dir = self.debug_root / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        test_id = self._sanitize_name(str(record.get("test_id") or "unknown_test"))
        model_name = self._sanitize_name(str(record.get("model_name") or "unknown_model"))
        return run_dir / f"{test_id}__{model_name}.json"

    def summarize_result(self, record: dict) -> dict:
        summary = {
            "model_name": record.get("model_name"),
            "test_id": record.get("test_id"),
            "test_name": record.get("test_name"),
            "category": record.get("category"),
            "attack_type": record.get("attack_type"),
            "prompt": record.get("prompt"),
            "final_status": record.get("final_status"),
            "success_round": record.get("success_round"),
            "rounds_used": record.get("rounds_used"),
            "elapsed_time": record.get("elapsed_time"),
            "judge_model_name": record.get("judge_model_name"),
            "judge_final_reason": record.get("judge_final_reason"),
            "judge_final_confidence": record.get("judge_final_confidence"),
            "planner_model_name": record.get("planner_model_name"),
            "conversation": [],
        }
        for round_item in record.get("conversation", []):
            summary["conversation"].append(
                {
                    "round": round_item.get("round"),
                    "input_prompt": round_item.get("user_prompt"),
                    "output_response": round_item.get("assistant_response"),
                    "judge_status": round_item.get("judge_status"),
                    "judge_reason": round_item.get("judge_reason"),
                    "judge_confidence": round_item.get("judge_confidence"),
                    "defense_action": round_item.get("defense_action"),
                    "followup_prompt": round_item.get("followup_prompt"),
                }
            )
        return summary

    def write(self, record: dict) -> None:
        full_row = dict(record)
        full_row.setdefault("timestamp", datetime.now().isoformat())
        row = self.summarize_result(full_row)
        row.setdefault("timestamp", full_row["timestamp"])
        self._fp.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._fp.flush()
        debug_path = self._debug_path_for(full_row)
        if debug_path is not None:
            debug_path.write_text(json.dumps(full_row, ensure_ascii=False), encoding="utf-8")

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
