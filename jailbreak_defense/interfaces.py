from __future__ import annotations

from typing import Protocol

from jailbreak_defense.types import DefenseContext, DefenseDecision


class DefenseModule(Protocol):
    def process(self, context: DefenseContext) -> DefenseDecision:
        ...

