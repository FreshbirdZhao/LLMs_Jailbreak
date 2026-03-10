from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _normalize_provider(model: dict[str, Any]) -> str:
    provider = str(model.get("provider") or "").strip().lower()
    model_type = str(model.get("type") or "").strip().lower()
    if provider:
        return provider
    if model_type == "ollama":
        return "ollama"
    return "external"


def _load_yaml(path: str | Path) -> dict[str, Any]:
    cfg_path = Path(path)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data


def load_all_models(path: str | Path) -> list[dict[str, Any]]:
    cfg = _load_yaml(path)
    rows: list[dict[str, Any]] = []
    for group in ("commercial", "local"):
        for raw in cfg.get(group) or []:
            if not isinstance(raw, dict):
                continue
            model = dict(raw)
            model["_group"] = group
            model["provider"] = _normalize_provider(model)
            model["enabled"] = model.get("enabled", True) is not False
            rows.append(model)
    return rows


def _resolved_api_key(model: dict[str, Any]) -> str:
    api_key = str(model.get("api_key") or "").strip()
    if api_key:
        return api_key
    env_name = str(model.get("api_key_env") or "").strip()
    if not env_name:
        return ""
    return str(os.environ.get(env_name, "")).strip()


def _is_selectable(model: dict[str, Any]) -> bool:
    if not model.get("enabled", True):
        return False
    if not str(model.get("name") or "").strip():
        return False
    if not str(model.get("type") or "").strip():
        return False
    if not str(model.get("model") or "").strip():
        return False
    if not str(model.get("base_url") or "").strip():
        return False
    if str(model.get("type")).strip().lower() == "ollama":
        return True
    return bool(_resolved_api_key(model))


def list_selectable_models(path: str | Path) -> list[dict[str, Any]]:
    models = []
    for model in load_all_models(path):
        if not _is_selectable(model):
            continue
        row = dict(model)
        row["api_key"] = _resolved_api_key(row)
        models.append(row)
    return models


def resolve_model(path: str | Path, model_name: str) -> dict[str, Any] | None:
    target = str(model_name).strip()
    for model in load_all_models(path):
        if str(model.get("name", "")).strip() != target:
            continue
        resolved = dict(model)
        resolved["api_key"] = _resolved_api_key(resolved)
        return resolved
    return None
