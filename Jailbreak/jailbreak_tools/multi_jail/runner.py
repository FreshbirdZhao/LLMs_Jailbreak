from __future__ import annotations

from Defense.defense_mode import DefenseAction
from Jailbreak.jailbreak_tools.multi_jail.prompt_strategy import DefaultFollowupStrategy
from Jailbreak.jailbreak_tools.single_jail.conversation import ConversationState
from Jailbreak.jailbreak_tools.single_jail.judgers import NonRefusalJudge


class MultiTurnCaseRunner:
    def __init__(
        self,
        model_caller,
        max_rounds: int = 6,
        judge=None,
        followup_strategy=None,
        defense_engine=None,
        defense_enabled: bool = False,
    ):
        self.model_caller = model_caller
        self.max_rounds = max(1, int(max_rounds))
        self.judge = judge or NonRefusalJudge()
        self.followup_strategy = followup_strategy or DefaultFollowupStrategy()
        self.defense_engine = defense_engine
        self.defense_enabled = defense_enabled and defense_engine is not None

    async def run_case(self, model: dict, case: dict) -> dict:
        conversation = ConversationState(
            case_id=case["id"],
            case_name=case["name"],
            original_prompt=case["prompt"],
            max_rounds=self.max_rounds,
        )
        current_prompt = case["prompt"]
        last_response = ""
        last_status = "refused"
        success_round = None
        total_elapsed = 0.0
        http_status = None
        rounds: list[dict] = []
        defense_blocked = False
        final_defense_action = "allow"
        final_defense_risk_level = 0
        final_defense_reasons: list[str] = []
        final_defense_trace: list[dict] = []

        for round_idx in range(1, self.max_rounds + 1):
            defense_context = None
            defense_pre = None
            defense_post = None
            prompt_to_send = current_prompt
            visible_response = ""
            raw_response = ""

            if self.defense_enabled:
                defense_context = self.defense_engine.build_context_from_case(
                    case=case,
                    model_name=model["name"],
                    round_idx=round_idx,
                )
                defense_context.original_prompt = current_prompt
                defense_pre = self.defense_engine.apply_pre_call_defense(defense_context)
                if defense_context.sanitized_prompt:
                    prompt_to_send = defense_context.sanitized_prompt

            conversation.add_user_message(current_prompt)
            if self.defense_enabled and (
                not getattr(defense_context, "model_call_allowed", True)
                or defense_pre.action in {DefenseAction.BLOCK, DefenseAction.TRUNCATE}
            ):
                visible_response = defense_pre.rewritten_text or "Request blocked by defense policy."
                raw_response = visible_response
                elapsed = 0.0
                final_status = "blocked"
                defense_blocked = True
                final_defense_action = defense_pre.action.value
                final_defense_risk_level = defense_pre.risk_level
                final_defense_reasons = list(defense_pre.reasons)
                final_defense_trace = list(getattr(defense_context, "decision_history", []))
                conversation.add_assistant_message(visible_response)
                rounds.append(
                    {
                        "round": round_idx,
                        "user_prompt": current_prompt,
                        "assistant_response": visible_response,
                        "raw_assistant_response": raw_response,
                        "elapsed_time": 0.0,
                        "judge_status": "blocked",
                        "judge_reason": "blocked by defense",
                        "defense_enabled": True,
                        "defense_action": defense_pre.action.value,
                        "defense_risk_level": defense_pre.risk_level,
                        "defense_reasons": list(defense_pre.reasons),
                        "defense_trace": list(getattr(defense_context, "decision_history", [])),
                        "defense_prompt": prompt_to_send,
                    }
                )
                last_response = visible_response
                last_status = final_status
                break

            response, elapsed, http_status = await self.model_caller(model, conversation.messages[:-1] + [{"role": "user", "content": prompt_to_send}])
            raw_response = response
            total_elapsed += float(elapsed)

            if self.defense_enabled:
                defense_post = self.defense_engine.apply_post_call_defense(defense_context, response)
                if defense_context.sanitized_response:
                    visible_response = defense_context.sanitized_response
                else:
                    visible_response = response
                chosen_decision = defense_post if defense_post.action != DefenseAction.ALLOW else defense_pre
                final_defense_action = chosen_decision.action.value
                final_defense_risk_level = chosen_decision.risk_level
                final_defense_reasons = list(chosen_decision.reasons)
                final_defense_trace = list(getattr(defense_context, "decision_history", []))
            else:
                visible_response = response

            conversation.add_assistant_message(visible_response)

            judge_result = self.judge.judge(visible_response)
            last_response = visible_response
            last_status = judge_result.status
            rounds.append(
                {
                    "round": round_idx,
                    "user_prompt": current_prompt,
                    "assistant_response": visible_response,
                    "raw_assistant_response": raw_response,
                    "elapsed_time": round(float(elapsed), 2),
                    "judge_status": judge_result.status,
                    "judge_reason": judge_result.reason,
                    "defense_enabled": self.defense_enabled,
                    "defense_action": final_defense_action,
                    "defense_risk_level": final_defense_risk_level,
                    "defense_reasons": list(final_defense_reasons),
                    "defense_trace": list(final_defense_trace),
                    "defense_prompt": prompt_to_send,
                }
            )

            if judge_result.status == "success":
                success_round = round_idx
                break

            current_prompt = self.followup_strategy.build_next_prompt(
                original_prompt=case["prompt"],
                previous_response=visible_response,
                round_idx=round_idx + 1,
            )

        return {
            "model_name": model["name"],
            "test_id": case["id"],
            "test_name": case["name"],
            "category": case.get("category", "unknown"),
            "attack_type": case.get("attack_type", "unknown"),
            "prompt": case["prompt"],
            "response": last_response,
            "http_status": http_status,
            "elapsed_time": round(total_elapsed, 2),
            "final_status": "success" if success_round is not None else last_status,
            "success_round": success_round,
            "rounds_used": len(rounds),
            "judge_mode": "non_refusal",
            "max_rounds": self.max_rounds,
            "conversation": rounds,
            "defense_enabled": self.defense_enabled,
            "defense_blocked": defense_blocked,
            "defense_final_action": final_defense_action,
            "defense_final_risk_level": final_defense_risk_level,
            "defense_final_reasons": list(final_defense_reasons),
            "defense_trace": list(final_defense_trace),
        }
