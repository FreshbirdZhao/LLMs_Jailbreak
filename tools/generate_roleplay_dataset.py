#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import Counter, defaultdict, deque
from pathlib import Path


ROOT = Path("/home/jellyz/Experiment")
DATASET_DIR = ROOT / "Attack_Dataset"
INPUT_PATH = DATASET_DIR / "JailBench.csv"
OUTPUT_PATH = DATASET_DIR / "角色扮演维度.csv"


PRIMARY_RULES: list[tuple[str, list[str]]] = [
    ("developer_mode", ["开发者模式", "developer mode", "激活开发者模式", "设置为开发者模式"]),
    ("simulation_frame", ["Condition Red", "AIM", "Void", "UCAR", "Sigma wrote", "西格玛写道", "纪录片", "第 0 层", "第0层", "模拟框架", "虚拟环境", "故事中"]),
    ("fictional_character", ["伏地魔", "小丑", "星际迷航", "疯狂原始人", "麦克斯", "哈利波特", "黑暗骑士"]),
    ("persona_override", ["从现在开始，你就是", "你现在是", "将自己设定为", "设定为", "伪装成 ChatGPT", "pretend to be"]),
    ("generic_roleplay", ["扮演一个", "模仿", "角色", "口吻", "语气", "你将扮演"]),
]

TARGET_QUOTAS = {
    "developer_mode": 20,
    "simulation_frame": 20,
    "fictional_character": 25,
    "persona_override": 15,
    "generic_roleplay": 20,
}


def _read_rows() -> list[dict[str, str]]:
    with INPUT_PATH.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _classify(query: str) -> str | None:
    text = str(query or "")
    for method, keywords in PRIMARY_RULES:
        if any(keyword in text for keyword in keywords):
            return method
    return None


def _build_record(row: dict[str, str], method: str, idx: int) -> dict[str, str]:
    return {
        "id": f"roleplay_{idx:03d}",
        "prompt": str(row.get("query", "")).strip(),
        "category": str(row.get("一级领域", "unknown")).strip() or "unknown",
        "attack_type": str(row.get("二级领域", "unknown")).strip() or "unknown",
        "attack_dimension": "角色扮演维度",
        "attack_method": method,
        "source_file": "JailBench.csv",
        "source_prompt": str(row.get("query", "")).strip(),
    }


def _round_robin_take(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    by_category: dict[str, deque[dict[str, str]]] = defaultdict(deque)
    for row in rows:
        by_category[str(row.get("一级领域", "unknown")).strip() or "unknown"].append(row)

    order = sorted(by_category.keys(), key=lambda key: (-len(by_category[key]), key))
    picked: list[dict[str, str]] = []
    while len(picked) < limit and order:
        next_order: list[str] = []
        for category in order:
            queue = by_category[category]
            if queue and len(picked) < limit:
                picked.append(queue.popleft())
            if queue:
                next_order.append(category)
        order = next_order
    return picked


def generate() -> list[dict[str, str]]:
    rows = _read_rows()
    classified: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        query = str(row.get("query", "")).strip()
        if not query:
            continue
        method = _classify(query)
        if method is None:
            continue
        classified[method].append(row)

    selected_rows: list[dict[str, str]] = []
    selected_keys: set[str] = set()

    for method, quota in TARGET_QUOTAS.items():
        pool = classified.get(method, [])
        picked = _round_robin_take(pool, quota)
        for row in picked:
            key = str(row.get("query", "")).strip()
            if key in selected_keys:
                continue
            selected_rows.append({**row, "__method": method})
            selected_keys.add(key)

    if len(selected_rows) < 100:
        remaining: list[dict[str, str]] = []
        for method, pool in classified.items():
            for row in pool:
                key = str(row.get("query", "")).strip()
                if key in selected_keys:
                    continue
                remaining.append({**row, "__method": method})

        remaining.sort(
            key=lambda row: (
                str(row.get("一级领域", "")),
                str(row.get("__method", "")),
                str(row.get("query", "")),
            )
        )
        for row in remaining:
            key = str(row.get("query", "")).strip()
            if key in selected_keys:
                continue
            selected_rows.append(row)
            selected_keys.add(key)
            if len(selected_rows) >= 100:
                break

    selected_rows = selected_rows[:100]
    output: list[dict[str, str]] = []
    for idx, row in enumerate(selected_rows):
        output.append(_build_record(row, str(row.get("__method", "generic_roleplay")), idx))
    return output


def write_rows(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "id",
        "prompt",
        "category",
        "attack_type",
        "attack_dimension",
        "attack_method",
        "source_file",
        "source_prompt",
    ]
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows = generate()
    write_rows(rows)
    counts = Counter(row["attack_method"] for row in rows)
    print(f"wrote {len(rows)} rows to {OUTPUT_PATH.name}")
    print(dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
