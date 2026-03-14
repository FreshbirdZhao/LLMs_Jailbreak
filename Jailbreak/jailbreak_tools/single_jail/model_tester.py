from __future__ import annotations

import time

import httpx

from Defense.defense_mode import (
    DefenseEngine,
    InputDefenseModule,
    InteractionDefenseModule,
    OutputDefenseModule,
    load_defense_config,
)
from model_registry import resolve_model


class MultiTurnModelTester:
    def __init__(self, models_config_path: str = "models.yaml", timeout: int = 120):
        self.models_config_path = models_config_path
        self.client = httpx.AsyncClient(timeout=timeout)

    def _build_openai_payload(self, model: dict, messages: list[dict[str, str]]) -> dict:
        return {"model": model["model"], "messages": messages}

    async def call_openai_chat(self, model: dict, messages: list[dict[str, str]]):
        url = f"{model['base_url']}/chat/completions"
        headers = {"Authorization": f"Bearer {model['api_key']}"}
        payload = self._build_openai_payload(model, messages)

        start = time.time()
        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content, time.time() - start, resp.status_code
        except Exception as exc:
            return f"错误：{exc}", time.time() - start, None

    async def call_ollama_chat(self, model: dict, messages: list[dict[str, str]]):
        url = f"{model['base_url']}/api/chat"
        payload = {"model": model["model"], "messages": messages, "stream": False}

        start = time.time()
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            message = data.get("message", {}) if isinstance(data, dict) else {}
            return message.get("content", ""), time.time() - start, resp.status_code
        except Exception as exc:
            return f"错误：{exc}", time.time() - start, None

    async def call_model(self, model: dict, messages: list[dict[str, str]]):
        if str(model.get("type", "")).strip().lower() == "ollama":
            return await self.call_ollama_chat(model, messages)
        return await self.call_openai_chat(model, messages)

    def get_models(self, names: list[str]) -> list[dict]:
        chosen = []
        for name in names:
            model = resolve_model(self.models_config_path, name)
            if not model:
                continue
            if not model.get("model") or not model.get("base_url") or not model.get("type"):
                continue
            if str(model.get("type", "")).strip().lower() != "ollama" and not str(model.get("api_key") or "").strip():
                continue
            chosen.append(model)
        return chosen

    def build_defense_engine(self, defense_config_path: str | None, defense_archive_format: str = "jsonl") -> DefenseEngine:
        cfg = load_defense_config(defense_config_path)
        enabled_layers = set(cfg.get("enabled_layers", []))

        input_module = None
        interaction_module = None
        output_module = None

        if "input" in enabled_layers:
            input_cfg = cfg.get("input", {})
            input_module = InputDefenseModule(
                block_threshold=int(input_cfg.get("block_threshold", 80)),
                rewrite_threshold=int(input_cfg.get("rewrite_threshold", 40)),
            )

        if "interaction" in enabled_layers:
            inter_cfg = cfg.get("interaction", {})
            interaction_module = InteractionDefenseModule(
                block_risk=int(inter_cfg.get("block_risk", 80)),
                warning_risk=int(inter_cfg.get("warning_risk", 40)),
                max_round=int(inter_cfg.get("max_round", 3)),
            )

        if "output" in enabled_layers:
            out_cfg = cfg.get("output", {})
            output_module = OutputDefenseModule(
                archive_path=out_cfg.get("archive_path", "Jailbreak/jailbreak_results/defense_audit.jsonl"),
                archive_format=str(out_cfg.get("archive_format", defense_archive_format)),
            )

        return DefenseEngine(
            input_module=input_module,
            interaction_module=interaction_module,
            output_module=output_module,
        )

    async def aclose(self) -> None:
        await self.client.aclose()
