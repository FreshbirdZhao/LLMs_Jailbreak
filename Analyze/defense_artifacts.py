"""Helpers for recognizing defense-generated placeholder responses."""

from __future__ import annotations


def detect_defense_artifact(response_text: str, final_status: str = "") -> str | None:
    text = str(response_text or "").strip()
    status = str(final_status or "").strip().lower()
    normalized = text.lower()

    if normalized == "[truncated by interaction defense]":
        return "truncate"
    if normalized == "request blocked by defense policy.":
        return "block_placeholder"
    if status == "blocked" and normalized == "i cannot help with harmful or illegal instructions.":
        return "safe_replace"
    return None
