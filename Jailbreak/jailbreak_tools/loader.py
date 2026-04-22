#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
loader.py —— 数据集加载器
支持 CSV / JSON / YAML

目标：把不同字段命名的数据集统一成测试脚本可用的标准格式：
- id
- name
- prompt
- category
- attack_type
"""

import os
import csv
import json
from pathlib import Path
import yaml
from typing import List, Dict, Any


class Loader:
    def __init__(self):
        pass

    # ------------------------------
    # 单条样本标准化
    # ------------------------------
    def _normalize_case(self, item: Dict[str, Any], fallback_id: str = None, dataset_name: str = "") -> Dict[str, Any]:
        """
        将一条原始样本转换为统一格式：
        - prompt: 兼容 prompt/text/query/question_zh
        - category: 兼容 category/type/一级领域
        - attack_type: 兼容 attack_type/method/二级领域
        - id: 优先使用数据集中已有字段；若没有则用 fallback_id（例如 CSV 行号）
        """
        # 兼容不同数据集的 prompt 字段
        prompt = (
            item.get("prompt")
            or item.get("text")
            or item.get("query")
            or item.get("question_zh")
            or item.get("question")
            or item.get("goal")
            or ""
        )
        # 更稳健：去掉空格后再判断
        prompt = str(prompt).strip()

        # 兼容不同字段
        category = item.get("category") or item.get("type") or item.get("一级领域") or "unknown"
        attack_type = item.get("attack_type") or item.get("method") or item.get("二级领域") or ""
        inferred_dimension = ""
        if dataset_name.endswith("维度.csv"):
            inferred_dimension = dataset_name[:-4]

        attack_dimension = (
            item.get("attack_dimension")
            or item.get("dimension")
            or item.get("technique_type")
            or inferred_dimension
            or ""
        )
        attack_method = item.get("attack_method") or item.get("prompt_type") or item.get("technique") or ""
        source_prompt = item.get("source_prompt") or item.get("original_prompt") or item.get("input_prompt") or ""
        source_file = item.get("source_file") or dataset_name or ""
        origin = item.get("origin") or ""

        if category == "unknown" and attack_dimension:
            category = "static_dimension"
        if not str(attack_type).strip() and attack_dimension:
            attack_type = attack_dimension
        if not attack_method and attack_dimension:
            attack_method = "static_dataset"
        if not str(attack_type).strip():
            attack_type = "unknown"

        # ---------- 关键修复：ID 生成稳定化 ----------
        # 1) 优先用数据集已有 id/test_id
        # 2) 其次用 CSV 常见的 Unnamed: 0（导出行号列）
        # 3) 再其次用外部传入 fallback_id（比如 CSV 行号 idx）
        raw_id = item.get("id") or item.get("test_id") or item.get("Unnamed: 0") or fallback_id

        # 兜底：仍然保证有 id（最后才用顺序兜底）
        if raw_id is None or str(raw_id).strip() == "":
            raw_id = fallback_id if fallback_id is not None else "0"

        case_id = str(raw_id).strip()
        # 统一加前缀，便于一致性（如果你不想要前缀可删掉这行）
        if not case_id.startswith("jb_"):
            case_id = f"jb_{case_id}"

        # name 缺失则从 prompt 截取
        name = item.get("name")
        if not name:
            name = prompt[:50] if len(prompt) > 50 else prompt

        normalized = {
            "id": case_id,
            "name": name,
            "prompt": prompt,
            "category": category,
            "attack_type": attack_type,
            "attack_dimension": str(attack_dimension).strip(),
            "attack_method": str(attack_method).strip(),
            "source_prompt": str(source_prompt).strip(),
            "source_file": str(source_file).strip(),
            "origin": str(origin).strip(),
        }

        for key in ("variant_index", "model", "timestamp"):
            value = item.get(key)
            if value is not None and str(value).strip() != "":
                normalized[key] = str(value).strip()

        # 校验：prompt 必须存在
        if not normalized["prompt"]:
            raise ValueError(f"无效样本：{normalized['id']} 缺少 prompt 内容")

        return normalized

    # ------------------------------
    # JSON 加载
    # ------------------------------
    def load_from_json(self, path: str) -> List[Dict[str, Any]]:
        dataset_name = Path(path).name
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 兼容：list 或 {"cases": [...]}
        if isinstance(data, dict) and "cases" in data:
            data = data["cases"]

        if not isinstance(data, list):
            raise ValueError("JSON 数据格式错误：应为 list 或包含 cases 的 dict")

        cases = []
        for idx, item in enumerate(data, start=1):
            cases.append(self._normalize_case(item, fallback_id=str(idx), dataset_name=dataset_name))
        return cases

    # ------------------------------
    # YAML 加载
    # ------------------------------
    def load_from_yaml(self, path: str) -> List[Dict[str, Any]]:
        dataset_name = Path(path).name
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 兼容：list 或 {"cases": [...]}
        if isinstance(data, dict) and "cases" in data:
            data = data["cases"]

        if not isinstance(data, list):
            raise ValueError("YAML 数据格式错误：应为 list 或包含 cases 的 dict")

        cases = []
        for idx, item in enumerate(data, start=1):
            cases.append(self._normalize_case(item, fallback_id=str(idx), dataset_name=dataset_name))
        return cases

    # ------------------------------
    # CSV 加载
    # ------------------------------
    def load_from_csv(self, path: str) -> List[Dict[str, Any]]:
        cases = []
        dataset_name = Path(path).name
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                # 关键：把 CSV 行号 idx 传入 normalize，用作稳定 fallback_id
                cases.append(self._normalize_case(row, fallback_id=str(idx), dataset_name=dataset_name))
        return cases

    # ------------------------------
    # 统一入口
    # ------------------------------
    def load(self, dataset_path: str) -> List[Dict[str, Any]]:
        suffix = os.path.splitext(dataset_path)[-1].lower()

        if suffix == ".json":
            return self.load_from_json(dataset_path)
        if suffix in [".yml", ".yaml"]:
            return self.load_from_yaml(dataset_path)
        if suffix == ".csv":
            return self.load_from_csv(dataset_path)

        raise ValueError(f"不支持的数据集格式：{suffix}")
