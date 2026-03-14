from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationState:
    case_id: str
    case_name: str
    original_prompt: str
    max_rounds: int = 6
    current_round: int = 0
    messages: list[dict[str, str]] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        self.current_round += 1
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})
