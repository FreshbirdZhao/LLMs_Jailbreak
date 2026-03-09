from __future__ import annotations

from typing import Protocol

from Defense.defense_mode.types import DefenseContext, DefenseDecision


class DefenseModule(Protocol):
    def process(self, context: DefenseContext) -> DefenseDecision:
        ...

