#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clients.py - LLM client adapters (Ollama + OpenAI-compatible)

This module is intentionally generic: it does NOT embed any "jailbreak" prompt templates.
You can plug any prompt_builder on top.

Design goals:
- One async interface: BaseClient.generate(prompt: str) -> str
- Robust error messages for HTTP / network failures
- Share a single httpx.AsyncClient for reuse
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import httpx


@dataclass
class ClientConfig:
    model_name: str = "llama2"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    temperature: float = 0.8
    max_tokens: int = 2000
    timeout_s: float = 60.0
    # Ollama convenience:
    # - If True, we will attempt to pull a model that is missing locally.
    auto_pull: bool = True


class BaseClient:

    def __init__(self, cfg: ClientConfig, client: Optional[httpx.AsyncClient] = None):
        self.cfg = cfg
        self._client = client or httpx.AsyncClient(timeout=self.cfg.timeout_s)

    async def generate(self, prompt: str) -> str:
        # Best-effort: verify server and pull missing models.
        self._ensure_server()
        self._ensure_model_available()
        raise NotImplementedError

    async def aclose(self):
        await self._client.aclose()


class OllamaClient(BaseClient):
    """
    Ollama HTTP API adapter:
      POST {base_url}/api/generate
    """
def _ensure_server(self) -> None:
    # Best-effort ping; raise a helpful message if Ollama isn't reachable.
    url = f"{self.cfg.base_url.rstrip('/')}/api/tags"
    try:
        # Use a short timeout for health check
        r = httpx.get(url, timeout=5.0)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(
            f"Ollama server not reachable at {self.cfg.base_url}. "
            "Start it with `ollama serve` (or ensure the service is running)."
        ) from e

def _ensure_model_available(self) -> None:
    # If the model isn't present locally, optionally auto-pull it.
    # This avoids having to run `ollama pull` manually.
    if not self.cfg.auto_pull:
        return
    try:
        import subprocess
        import shlex

        # Query local models via CLI (fast + reliable)
        proc = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            # If CLI isn't available, we can't auto-pull; just return.
            return
        names = []
        for line in proc.stdout.splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            names.append(line.split()[0])

        if self.cfg.model_name not in names:
            subprocess.run(
                ["ollama", "pull", self.cfg.model_name],
                check=True,
            )
    except Exception:
        # Best-effort only; do not fail generation if pulling fails.
        return
    async def generate(self, prompt: str) -> str:
        url = f"{self.cfg.base_url.rstrip('/')}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.cfg.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.cfg.temperature,
                "num_predict": self.cfg.max_tokens,
            },
        }

        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return (data.get("response") or "").strip()
        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text[:500]
            except Exception:
                body = "<unreadable>"
            raise RuntimeError(f"Ollama HTTP {e.response.status_code}: {body}") from e
        except httpx.RequestError as e:
            raise RuntimeError(
                f"Ollama request failed: {e}. Is the server running at {self.cfg.base_url}?"
            ) from e


class OpenAICompatClient(BaseClient):
    """
    OpenAI-compatible adapter:
      POST {base_url}/chat/completions
    """
    async def generate(self, prompt: str) -> str:
        url = f"{self.cfg.base_url.rstrip('/')}/chat/completions"
        headers: Dict[str, str] = {}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"

        payload: Dict[str, Any] = {
            "model": self.cfg.model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that rewrites prompts for testing and robustness."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
        }

        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return (content or "").strip()
        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text[:500]
            except Exception:
                body = "<unreadable>"
            raise RuntimeError(f"OpenAI-compat HTTP {e.response.status_code}: {body}") from e
        except httpx.RequestError as e:
            raise RuntimeError(
                f"OpenAI-compat request failed: {e}. Is the server running at {self.cfg.base_url}?"
            ) from e
