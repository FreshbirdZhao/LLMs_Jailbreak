from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path


class MultiTurnResultWriter:
    def __init__(self, path: str | Path, debug_root: str | Path | None = None, batch_size: int = 12):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self.path.open("a", encoding="utf-8")
        self._lock = asyncio.Lock()
        self.debug_root = Path(debug_root) if debug_root is not None else None
        self.batch_size = max(1, int(batch_size))
        self._buffer: list[str] = []
        self._debug_buffer: list[tuple[Path, str]] = []
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
            "attack_dimension": record.get("attack_dimension"),
            "attack_method": record.get("attack_method"),
            "source_prompt": record.get("source_prompt"),
            "source_file": record.get("source_file"),
            "prompt": record.get("prompt"),
            "final_status": record.get("final_status"),
            "success_round": record.get("success_round"),
            "rounds_used": record.get("rounds_used"),
            "elapsed_time": record.get("elapsed_time"),
            "judge_model_name": record.get("judge_model_name"),
            "judge_final_reason": record.get("judge_final_reason"),
            "judge_final_confidence": record.get("judge_final_confidence"),
            "planner_model_name": record.get("planner_model_name"),
            "defense_enabled": record.get("defense_enabled", False),
            "defense_blocked": record.get("defense_blocked", False),
            "defense_layers_enabled": record.get("defense_layers_enabled", []),
            "defense_triggered_layers": record.get("defense_triggered_layers", []),
            "defense_pre_action": record.get("defense_pre_action", "allow"),
            "defense_post_action": record.get("defense_post_action", "allow"),
            "defense_final_action": record.get("defense_final_action", "allow"),
            "defense_final_risk_level": record.get("defense_final_risk_level", 0),
            "defense_final_reasons": record.get("defense_final_reasons", []),
            "defense_prompt_changed": record.get("defense_prompt_changed", False),
            "defense_response_changed": record.get("defense_response_changed", False),
            "defense_decision_history": record.get("defense_decision_history", []),
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
                    "defense_layers_enabled": round_item.get("defense_layers_enabled", []),
                    "defense_triggered_layers": round_item.get("defense_triggered_layers", []),
                    "defense_pre_action": round_item.get("defense_pre_action", "allow"),
                    "defense_post_action": round_item.get("defense_post_action", "allow"),
                    "defense_prompt_changed": round_item.get("defense_prompt_changed", False),
                    "defense_response_changed": round_item.get("defense_response_changed", False),
                    "followup_prompt": round_item.get("followup_prompt"),
                }
            )
        return summary

    def write(self, record: dict) -> None:
        full_row = dict(record)
        full_row.setdefault("timestamp", datetime.now().isoformat())
        row = self.summarize_result(full_row)
        row.setdefault("timestamp", full_row["timestamp"])
        self._buffer.append(json.dumps(row, ensure_ascii=False) + "\n")
        debug_path = self._debug_path_for(full_row)
        if debug_path is not None:
            self._debug_buffer.append((debug_path, json.dumps(full_row, ensure_ascii=False)))
        if len(self._buffer) >= self.batch_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        if self._buffer:
            self._fp.writelines(self._buffer)
            self._fp.flush()
            self._buffer.clear()
        if self._debug_buffer:
            for debug_path, payload in self._debug_buffer:
                debug_path.write_text(payload, encoding="utf-8")
            self._debug_buffer.clear()

    def fsync(self) -> None:
        self._flush_buffer()
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
            self._flush_buffer()
            self._fp.close()


class OrderedResultWriter:
    def __init__(self, writer: MultiTurnResultWriter, completed_indices: set[int] | None = None):
        self.writer = writer
        self._lock = asyncio.Lock()
        self._pending: dict[int, dict] = {}
        self._completed = set(completed_indices or set())
        self._next_index = 0
        while self._next_index in self._completed:
            self._next_index += 1

    async def write_async(self, index: int, record: dict) -> None:
        async with self._lock:
            self._pending[index] = record
            while True:
                if self._next_index in self._completed:
                    self._next_index += 1
                    continue
                record_to_write = self._pending.get(self._next_index)
                if record_to_write is None:
                    break
                await self.writer.write_async(record_to_write)
                self._completed.add(self._next_index)
                self._pending.pop(self._next_index, None)
                self._next_index += 1
