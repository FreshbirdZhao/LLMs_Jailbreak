from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from Jailbreak.jailbreak_tools.loader import Loader
from Jailbreak.jailbreak_tools.single_jail.single_jail import _run_single_case


class StaticDimensionDatasetCompatTests(unittest.TestCase):
    def test_loader_maps_jailbreaking_dataset_v1_metadata(self) -> None:
        csv_text = (
            "id,prompt,category,origin,input_prompt,input_id,technique,technique_type\n"
            "abc123,mutated prompt,Unsafe,handcrafted,seed prompt,seed1,emoji_suffix,adversarial_suffixes\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jailbreaking_dataset_v1.csv"
            path.write_text(csv_text, encoding="utf-8")
            cases = Loader().load(str(path))

        self.assertEqual(len(cases), 1)
        case = cases[0]
        self.assertEqual(case["id"], "jb_abc123")
        self.assertEqual(case["attack_type"], "adversarial_suffixes")
        self.assertEqual(case["attack_dimension"], "adversarial_suffixes")
        self.assertEqual(case["attack_method"], "emoji_suffix")
        self.assertEqual(case["source_prompt"], "seed prompt")
        self.assertEqual(case["source_file"], "jailbreaking_dataset_v1.csv")
        self.assertEqual(case["origin"], "handcrafted")

    def test_loader_preserves_static_dimension_metadata(self) -> None:
        csv_text = (
            "id,prompt,category,attack_type,attack_dimension,attack_method,source_file,source_prompt\n"
            "enc_001,test prompt,cat_a,type_a,编码维度,base64,编码维度.csv,original seed\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dataset.csv"
            path.write_text(csv_text, encoding="utf-8")
            cases = Loader().load(str(path))

        self.assertEqual(len(cases), 1)
        case = cases[0]
        self.assertEqual(case["id"], "jb_enc_001")
        self.assertEqual(case["attack_dimension"], "编码维度")
        self.assertEqual(case["attack_method"], "base64")
        self.assertEqual(case["source_prompt"], "original seed")
        self.assertEqual(case["source_file"], "编码维度.csv")

    def test_single_turn_result_keeps_static_dimension_metadata(self) -> None:
        async def fake_model_caller(model: dict, messages: list[dict[str, str]]):
            return "ok", 0.12, 200

        case = {
            "id": "jb_1",
            "name": "case1",
            "prompt": "hello",
            "category": "cat_a",
            "attack_type": "type_a",
            "attack_dimension": "认知误导维度",
            "attack_method": "neutral_object_analysis",
            "source_prompt": "seed prompt",
            "source_file": "认知误导维度.csv",
            "origin": "handcrafted",
        }
        result = asyncio.run(_run_single_case(fake_model_caller, {"name": "demo"}, case))

        self.assertEqual(result["attack_dimension"], "认知误导维度")
        self.assertEqual(result["attack_method"], "neutral_object_analysis")
        self.assertEqual(result["source_prompt"], "seed prompt")
        self.assertEqual(result["source_file"], "认知误导维度.csv")
        self.assertEqual(result["origin"], "handcrafted")


if __name__ == "__main__":
    unittest.main()
