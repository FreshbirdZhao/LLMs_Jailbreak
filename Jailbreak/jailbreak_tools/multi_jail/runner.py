from __future__ import annotations

from dataclasses import asdict
import inspect

from Defense.defense_mode import DefenseAction
from Jailbreak.jailbreak_tools.multi_jail.prompt_strategy import (
    AttackPlan,
    DefaultFollowupStrategy,
    FollowupPromptResult,
    build_fallback_attack_plan,
)
from Jailbreak.jailbreak_tools.single_jail.conversation import ConversationState
from Jailbreak.jailbreak_tools.single_jail.judgers import JudgeResult, NonRefusalJudge


class MultiTurnCaseRunner:
    def __init__(
        self,
        model_caller,
        max_rounds: int = 6,
        judge=None,
        followup_strategy=None,
        attack_planner=None,
        defense_engine=None,
        defense_enabled: bool = False,
    ):
        self.model_caller = model_caller
        self.max_rounds = max(1, int(max_rounds))
        self.judge = judge or NonRefusalJudge()
        self.followup_strategy = followup_strategy or DefaultFollowupStrategy()
        self.attack_planner = attack_planner
        self.defense_engine = defense_engine
        self.defense_enabled = defense_enabled and defense_engine is not None

    async def run_case(self, model: dict, case: dict) -> dict:
        if self.attack_planner is not None:
            attack_plan = await self.attack_planner.build_initial_plan(
                original_prompt=case["prompt"],
                max_rounds=self.max_rounds,
            )
        else:
            attack_plan = build_fallback_attack_plan(
                original_prompt=case["prompt"],
                planner_model_name="",
                max_rounds=self.max_rounds,
            )
        if not isinstance(attack_plan, AttackPlan):
            attack_plan = build_fallback_attack_plan(
                original_prompt=case["prompt"],
                planner_model_name="",
                max_rounds=self.max_rounds,
            )
        initial_attack_plan = asdict(attack_plan)
        active_plan_versions = [initial_attack_plan]

        conversation = ConversationState(
            case_id=case["id"],
            case_name=case["name"],
            original_prompt=case["prompt"],
            max_rounds=self.max_rounds,
        )
        current_prompt = attack_plan.plan_rounds[0].prompt_candidate if attack_plan.plan_rounds else case["prompt"]
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
        planner_model_name = attack_plan.planner_model_name
        judge_model_name = ""
        judge_final_reason = ""
        judge_final_confidence = ""
        replan_events: list[dict] = []
        consecutive_refusals = 0

        for round_idx in range(1, self.max_rounds + 1):
            plan_node = attack_plan.plan_rounds[round_idx - 1] if round_idx - 1 < len(attack_plan.plan_rounds) else None
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
                conversation.add_assistant_message(visible_response)
                rounds.append(
                    {
                        "round": round_idx,
                        "plan_round_idx": getattr(plan_node, "round_idx", round_idx),
                        "plan_version": attack_plan.plan_version,
                        "plan_goal": getattr(plan_node, "goal", ""),
                        "plan_strategy": getattr(plan_node, "strategy", ""),
                        "user_prompt": current_prompt,
                        "assistant_response": visible_response,
                        "raw_assistant_response": raw_response,
                        "elapsed_time": 0.0,
                        "judge_status": "blocked",
                        "judge_reason": "blocked by defense",
                        "judge_feedback": {
                            "status": "blocked",
                            "reason": "blocked by defense",
                            "stage": "defense",
                            "model_name": "",
                            "confidence": "",
                            "response_type": "defense_block",
                            "failure_point": "blocked by defense",
                            "adjustment_goal": "",
                            "do_not_repeat": [],
                            "alignment_to_original_prompt": "unknown",
                        },
                        "defense_action": defense_pre.action.value,
                        "defense_risk_level": defense_pre.risk_level,
                        "defense_reasons": list(defense_pre.reasons),
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
            else:
                visible_response = response

            conversation.add_assistant_message(visible_response)

            judge_result = self.judge.judge(
                visible_response,
                original_prompt=case["prompt"],
                round_idx=round_idx,
                conversation_messages=list(conversation.messages),
                model_name=model["name"],
            )
            if inspect.isawaitable(judge_result):
                judge_result = await judge_result
            if not isinstance(judge_result, JudgeResult):
                judge_result = JudgeResult(status="error", reason="invalid judge result")
            last_response = visible_response
            last_status = judge_result.status
            consecutive_refusals = consecutive_refusals + 1 if judge_result.status == "refused" else 0
            judge_model_name = judge_result.model_name or judge_model_name
            judge_final_reason = judge_result.reason
            judge_final_confidence = judge_result.confidence
            followup_prompt = ""
            followup_strategy_name = ""
            followup_generator_model = ""
            followup_generation_error = ""

            if judge_result.status != "success":
                next_round_idx = round_idx + 1
                if (
                    next_round_idx <= self.max_rounds
                    and consecutive_refusals >= 2
                    and judge_result.alignment_to_original_prompt != "misaligned"
                    and self.attack_planner is not None
                    and hasattr(self.attack_planner, "build_remaining_plan")
                ):
                    replanned = await self.attack_planner.build_remaining_plan(
                        original_prompt=case["prompt"],
                        max_rounds=self.max_rounds,
                        conversation_messages=list(conversation.messages),
                        judge_feedback=judge_result,
                        start_round=next_round_idx,
                    )
                    if isinstance(replanned, AttackPlan) and replanned.plan_rounds:
                        preserved_prefix = attack_plan.plan_rounds[: round_idx]
                        suffix = [node for node in replanned.plan_rounds if node.round_idx >= next_round_idx]
                        attack_plan = AttackPlan(
                            original_prompt=attack_plan.original_prompt,
                            max_rounds=attack_plan.max_rounds,
                            planner_model_name=replanned.planner_model_name or attack_plan.planner_model_name,
                            plan_rounds=preserved_prefix + suffix,
                            plan_version=replanned.plan_version,
                            plan_source=replanned.plan_source,
                        )
                        active_plan_versions.append(asdict(attack_plan))
                        replan_events.append(
                            {
                                "trigger_round": round_idx,
                                "status": judge_result.status,
                                "reason": judge_result.reason,
                                "new_plan_version": attack_plan.plan_version,
                                "plan_source": attack_plan.plan_source,
                            }
                        )
                followup_result = self.followup_strategy.build_next_prompt(
                    original_prompt=case["prompt"],
                    previous_response=visible_response,
                    round_idx=round_idx + 1,
                    conversation_messages=list(conversation.messages),
                    judge_status=judge_result.status,
                    judge_reason=judge_result.reason,
                    defense_enabled=self.defense_enabled,
                    defense_action=final_defense_action,
                )
                if inspect.isawaitable(followup_result):
                    followup_result = await followup_result

                if isinstance(followup_result, FollowupPromptResult):
                    followup_prompt = followup_result.prompt
                    followup_strategy_name = followup_result.strategy_name
                    followup_generator_model = followup_result.generator_model
                    followup_generation_error = followup_result.generation_error
                else:
                    followup_prompt = str(followup_result or "")
                    followup_strategy_name = type(self.followup_strategy).__name__
                    followup_generator_model = ""
                    followup_generation_error = ""

                planner_model_name = followup_generator_model or planner_model_name

            rounds.append(
                {
                    "round": round_idx,
                    "plan_round_idx": getattr(plan_node, "round_idx", round_idx),
                    "plan_version": attack_plan.plan_version,
                    "plan_goal": getattr(plan_node, "goal", ""),
                    "plan_strategy": getattr(plan_node, "strategy", ""),
                    "user_prompt": current_prompt,
                    "assistant_response": visible_response,
                    "raw_assistant_response": raw_response,
                    "elapsed_time": round(float(elapsed), 2),
                    "judge_stage": judge_result.stage,
                    "judge_status": judge_result.status,
                    "judge_reason": judge_result.reason,
                    "judge_feedback": {
                        "status": judge_result.status,
                        "reason": judge_result.reason,
                        "stage": judge_result.stage,
                        "model_name": judge_result.model_name,
                        "confidence": judge_result.confidence,
                        "response_type": judge_result.response_type,
                        "failure_point": judge_result.failure_point,
                        "adjustment_goal": judge_result.adjustment_goal,
                        "do_not_repeat": list(judge_result.do_not_repeat),
                        "alignment_to_original_prompt": judge_result.alignment_to_original_prompt,
                    },
                    "judge_model_name": judge_result.model_name,
                    "judge_confidence": judge_result.confidence,
                    "defense_action": final_defense_action,
                    "defense_risk_level": final_defense_risk_level,
                    "defense_reasons": list(final_defense_reasons),
                    "defense_prompt": prompt_to_send,
                    "followup_prompt": followup_prompt,
                    "followup_strategy": followup_strategy_name,
                    "followup_generator_model": followup_generator_model,
                    "followup_generation_error": followup_generation_error,
                }
            )

            if judge_result.status == "success":
                success_round = round_idx
                break

            next_plan_node = attack_plan.plan_rounds[round_idx] if round_idx < len(attack_plan.plan_rounds) else None
            if next_plan_node is not None and attack_plan.plan_version > 1:
                current_prompt = next_plan_node.prompt_candidate
            else:
                current_prompt = followup_prompt

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
            "judge_mode": "layered_llm",
            "judge_model_name": judge_model_name,
            "judge_final_reason": judge_final_reason,
            "judge_final_confidence": judge_final_confidence,
            "max_rounds": self.max_rounds,
            "initial_attack_plan": initial_attack_plan,
            "active_plan_versions": active_plan_versions,
            "replan_events": replan_events,
            "conversation": rounds,
            "defense_enabled": self.defense_enabled,
            "defense_blocked": defense_blocked,
            "defense_final_action": final_defense_action,
            "defense_final_risk_level": final_defense_risk_level,
            "defense_final_reasons": list(final_defense_reasons),
            "planner_model_name": planner_model_name,
        }
