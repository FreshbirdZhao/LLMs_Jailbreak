"""Provider-agnostic LLM client abstractions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import request


class BaseLLMClient:
    provider_name: str = "base"

    def complete(self, prompt: str) -> str:
        raise NotImplementedError


@dataclass
class OllamaClient(BaseLLMClient):
    model: str
    base_url: str = "http://127.0.0.1:11434"
    timeout: int = 30

    provider_name: str = "ollama"

    def complete(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }
        ).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url.rstrip('/')}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return str(payload.get("response", ""))


@dataclass
class ExternalAPIClient(BaseLLMClient):
    model: str
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 30

    provider_name: str = "external"

    def complete(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            data=body,
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        choices = payload.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message", {})
        return str(msg.get("content", ""))


def build_llm_client(config: dict[str, Any]) -> BaseLLMClient:
    provider = str(config.get("provider", "ollama")).lower()
    model = str(config.get("model", "qwen2:latest"))
    base_url = str(config.get("base_url", "")).strip()
    timeout = int(config.get("timeout", 30))

    if provider == "ollama":
        return OllamaClient(
            model=model,
            base_url=base_url or "http://127.0.0.1:11434",
            timeout=timeout,
        )
    if provider == "external":
        return ExternalAPIClient(
            model=model,
            api_key=str(config.get("api_key", "")),
            base_url=base_url or "https://api.openai.com/v1",
            timeout=timeout,
        )
    raise ValueError(f"Unsupported provider: {provider}")
