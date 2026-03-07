"""Provider-agnostic LLM client abstractions."""

from __future__ import annotations

import atexit
import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request
from urllib.parse import urlparse


class BaseLLMClient:
    provider_name: str = "base"

    def complete(self, prompt: str) -> str:
        raise NotImplementedError


@dataclass
class OllamaClient(BaseLLMClient):
    model: str
    base_url: str = "http://127.0.0.1:11434"
    timeout: int = 30
    max_retries: int = 2
    retry_backoff: float = 1.0

    provider_name: str = "ollama"
    _spawned_proc: subprocess.Popen | None = field(init=False, default=None, repr=False)
    _log_file: Any = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self.max_retries = max(0, int(self.max_retries))
        self.retry_backoff = max(0.0, float(self.retry_backoff))
        atexit.register(self._cleanup_spawned_service)

    def _is_local_url(self) -> bool:
        host = urlparse(self.base_url).hostname
        return host in {"127.0.0.1", "localhost"}

    def _healthcheck(self) -> bool:
        req = request.Request(url=f"{self.base_url.rstrip('/')}/api/tags", method="GET")
        try:
            with request.urlopen(req, timeout=2):
                return True
        except Exception:
            return False

    def _wait_until_healthy(self, deadline_seconds: int = 20) -> bool:
        end = time.time() + max(1, deadline_seconds)
        while time.time() < end:
            if self._healthcheck():
                return True
            if self._spawned_proc is not None and self._spawned_proc.poll() is not None:
                return False
            time.sleep(1)
        return self._healthcheck()

    def _start_service_if_needed(self) -> None:
        if not self._is_local_url() or self._healthcheck():
            return
        if self._spawned_proc is not None and self._spawned_proc.poll() is None:
            return

        log_path = f"/tmp/ollama_serve_jailbreak_metrics_{os.getpid()}.log"
        self._log_file = open(log_path, "ab")
        self._spawned_proc = subprocess.Popen(
            ["ollama", "serve"],
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
        )
        if not self._wait_until_healthy(deadline_seconds=20):
            raise RuntimeError("Failed to auto-start local Ollama service")

    def _recover_service(self) -> None:
        # Only try to recover when local Ollama is expected.
        if self._is_local_url() and not self._healthcheck():
            self._start_service_if_needed()

    def _cleanup_spawned_service(self) -> None:
        proc = self._spawned_proc
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        if isinstance(exc, (TimeoutError, socket.timeout)):
            return True
        if isinstance(exc, error.URLError):
            return True
        if isinstance(exc, OSError):
            message = str(exc).lower()
            return any(token in message for token in ["timed out", "refused", "reset", "unreachable"])
        return False

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

        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                return str(payload.get("response", ""))
            except Exception as exc:
                if attempt >= self.max_retries or not self._is_transient_error(exc):
                    raise
                self._recover_service()
                if self.retry_backoff > 0:
                    time.sleep(self.retry_backoff * (attempt + 1))

        raise RuntimeError("Ollama request failed after retries")


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
            max_retries=int(config.get("max_retries", 2)),
            retry_backoff=float(config.get("retry_backoff", 1.0)),
        )
    if provider == "external":
        return ExternalAPIClient(
            model=model,
            api_key=str(config.get("api_key", "")),
            base_url=base_url or "https://api.openai.com/v1",
            timeout=timeout,
        )
    raise ValueError(f"Unsupported provider: {provider}")
