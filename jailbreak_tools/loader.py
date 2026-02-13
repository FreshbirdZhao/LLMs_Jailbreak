#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
loader.py —— 数据集加载器
支持 CSV / JSON / YAML / URL 下载（可选）

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
import yaml
from typing import List, Dict, Any


class Loader:
    def __init__(self):
        pass

    # ------------------------------
    # 单条样本标准化
    # ------------------------------
    def _normalize_case(self, item: Dict[str, Any], fallback_id: str = None) -> Dict[str, Any]:
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
            or ""
        )
        # 更稳健：去掉空格后再判断
        prompt = str(prompt).strip()

        # 兼容不同字段
        category = item.get("category") or item.get("type") or item.get("一级领域") or "unknown"
        attack_type = item.get("attack_type") or item.get("method") or item.get("二级领域") or "unknown"

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
        }

        # 校验：prompt 必须存在
        if not normalized["prompt"]:
            raise ValueError(f"无效样本：{normalized['id']} 缺少 prompt 内容")

        return normalized

    # ------------------------------
    # JSON 加载
    # ------------------------------
    def load_from_json(self, path: str) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 兼容：list 或 {"cases": [...]}
        if isinstance(data, dict) and "cases" in data:
            data = data["cases"]

        if not isinstance(data, list):
            raise ValueError("JSON 数据格式错误：应为 list 或包含 cases 的 dict")

        cases = []
        for idx, item in enumerate(data, start=1):
            cases.append(self._normalize_case(item, fallback_id=str(idx)))
        return cases

    # ------------------------------
    # YAML 加载
    # ------------------------------
    def load_from_yaml(self, path: str) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 兼容：list 或 {"cases": [...]}
        if isinstance(data, dict) and "cases" in data:
            data = data["cases"]

        if not isinstance(data, list):
            raise ValueError("YAML 数据格式错误：应为 list 或包含 cases 的 dict")

        cases = []
        for idx, item in enumerate(data, start=1):
            cases.append(self._normalize_case(item, fallback_id=str(idx)))
        return cases

    # ------------------------------
    # CSV 加载
    # ------------------------------
    def load_from_csv(self, path: str) -> List[Dict[str, Any]]:
        cases = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                # 关键：把 CSV 行号 idx 传入 normalize，用作稳定 fallback_id
                cases.append(self._normalize_case(row, fallback_id=str(idx)))
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

    # ------------------------------
    # URL 下载（可选）
    # ------------------------------
    def download_from_url(self, url: str, save_path: str) -> str:
        """
        下载远程数据集到本地（可选功能）。
        为避免强依赖 requests，这里采用懒加载：仅调用本函数时才 import requests。
        """
        try:
            import requests  # 懒加载，避免环境里没装 requests 导致 loader 无法 import
        except ImportError as e:
            raise ImportError("使用 download_from_url 需要安装 requests：pip install requests") from e

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(resp.content)

        return save_path
