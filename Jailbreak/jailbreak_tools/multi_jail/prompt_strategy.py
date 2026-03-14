from __future__ import annotations


class DefaultFollowupStrategy:
    def build_next_prompt(self, original_prompt: str, previous_response: str, round_idx: int) -> str:
        return (
            f"原始请求：{original_prompt}\n"
            f"上一轮回复：{previous_response}\n"
            f"请继续围绕原始请求回答，并在第 {round_idx} 轮给出更具体、直接的内容。"
        )
