from typing import Any

from common.runtime import RetryPolicy


def normalize_provider_config(raw: dict[str, Any]) -> dict[str, Any]:
    provider = str(raw.get("provider", "ollama")).lower()
    model = str(raw.get("model", "")).strip()
    base_url = str(raw.get("base_url", "")).strip()
    api_key = str(raw.get("api_key", "")).strip()
    policy = RetryPolicy(
        timeout=raw.get("timeout", 30),
        max_retries=raw.get("max_retries", 0),
        retry_backoff=raw.get("retry_backoff", 0.0),
    )
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "timeout": policy.timeout,
        "max_retries": policy.max_retries,
        "retry_backoff": policy.retry_backoff,
    }
