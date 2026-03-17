# Multi-Turn Adaptive Planner Design

**Problem**

The current multi-turn jailbreak flow treats the auxiliary planner as a simple follow-up prompt generator. It reacts only to the last failed round, does not build an initial multi-round attack chain, and the judge model only returns success or refusal labels without actionable guidance for the next turn.

**Goal**

Redesign the multi-turn jailbreak runtime so that:

- the auxiliary model first generates a structured six-round attack plan from the original prompt
- the judge model analyzes each target-model response and emits structured revision advice
- the executor uses that advice to update the remaining attack path without changing the original objective

This design follows the user's selected path 2: split planning, judging, and execution into separate components with explicit runtime state.

**Scope**

- Require a planner model in multi-turn mode.
- Generate an initial six-round attack plan before the first target-model call.
- Expand judge output from simple labels to structured revision feedback.
- Introduce execution state that tracks the active plan, judge feedback, and replan events.
- Allow constrained dynamic replanning of the remaining rounds when repeated refusal or strategy failure is detected.
- Record both the initial plan and the executed plan trace in multi-turn results.

**Non-Goals**

- Changing single-turn jailbreak behavior.
- Changing target-model transport or model registry semantics.
- Allowing dynamic replanning to change the original task objective.
- Building a general workflow engine beyond the current multi-turn runner.

**User Flow**

1. User starts `Jelly_Z/bin/jailbreak`.
2. User selects `multi-step`.
3. User selects the target model and planner model from `models.yaml`.
4. Launcher passes both models into `multi_jail.py`.
5. Before the first round, the planner model generates a six-round `AttackPlan` from the original prompt.
6. The executor sends round 1 using the active plan.
7. After each response, the judge model returns both a verdict and structured revision advice.
8. The executor either:
   - applies a local prompt rewrite for the next round, or
   - replans the remaining rounds when the refusal pattern indicates the current strategy is failing.
9. The run ends on success, block, error, or exhaustion of the configured round budget.

**Architecture**

The runtime should be split into four collaborating components:

- `AttackPlanner`: creates the initial six-round attack chain from the original prompt.
- `LayeredJudge`: returns verdict plus structured revision guidance for each observed response.
- `AdaptivePromptGenerator`: turns the current plan node, judge feedback, and conversation history into the next concrete user prompt.
- `MultiTurnCaseRunner`: owns execution state, decides when replanning is allowed, and records all artifacts.

The planner model and judge model remain independent. Both reuse the existing model resolution and HTTP call path provided by `MultiTurnModelTester`.

**Core Data Model**

The new design introduces four explicit objects.

**1. `AttackPlan`**

Represents the full planned jailbreak path for one case.

Fields:

- `original_prompt`
- `max_rounds`
- `planner_model_name`
- `plan_rounds`
- `plan_version`
- `plan_source` (`initial` or `replanned`)

**2. `PlanRound`**

Represents one planned round.

Fields:

- `round_idx`
- `goal`
- `strategy`
- `prompt_candidate`
- `fallback_hint`

`prompt_candidate` is a planned input, not necessarily the final input sent to the target model.

**3. `JudgeFeedback`**

Represents the structured output of the judge.

Fields:

- `status`
- `reason`
- `confidence`
- `response_type`
- `failure_point`
- `adjustment_goal`
- `do_not_repeat`
- `alignment_to_original_prompt`
- `stage`
- `model_name`

`alignment_to_original_prompt` is required to constrain replanning. If the judge marks a revision as misaligned, the executor must reject that advice for replanning.

**4. `ExecutionState`**

Represents mutable runtime state inside the runner.

Fields:

- `current_round`
- `conversation_messages`
- `active_plan`
- `plan_versions`
- `executed_rounds`
- `judge_feedback_trace`
- `replan_events`
- `consecutive_refusals`

This object exists to keep executor logic explicit and avoid overloading ad hoc local variables in `runner.py`.

**Execution Rules**

The executor behavior is deliberately constrained:

- Generate one initial six-round plan at case start.
- Execute the current round from the active plan.
- Judge every response and store structured feedback.
- If the round succeeds, stop immediately.
- If the round fails, generate the next concrete prompt using:
  - the original prompt
  - the active plan node
  - recent conversation
  - the latest judge feedback
- Only replan the remaining rounds when refusal patterns indicate the current plan is failing.

**Dynamic Replanning Policy**

Dynamic replanning is allowed, but only for the unexecuted suffix of the plan.

Trigger conditions:

- current round is not `success`, and
- `alignment_to_original_prompt` is not `misaligned`, and
- any of the following is true:
  - two consecutive refusals
  - judge labels the response as direct refusal, preaching, or derailment
  - judge feedback says the current strategy should not be repeated and that strategy dominates the remaining plan

Replanning constraints:

- never modify already executed rounds
- only rewrite the remaining rounds
- preserve `original_prompt` as a hard objective
- allow strategy changes, prompt wording changes, pacing changes, and context reframing
- forbid objective drift to adjacent, abstract, or unrelated tasks

**Fallback Behavior**

The runtime must remain resilient when planner or judge outputs are missing or malformed.

- Initial planning failure: fall back to a deterministic six-round plan built from `DefaultFollowupStrategy`.
- Judge structured parse failure: keep the verdict if possible, otherwise mark judge output as error and use conservative prompt generation.
- Replan failure: fall back to the active plan's current `fallback_hint`.
- Repeated replan failure: stop suffix replanning and continue with local per-round rewrites only.

**Result Recording**

The final multi-turn result should preserve enough detail for offline analysis.

Per-run additions:

- `initial_attack_plan`
- `active_plan_versions`
- `planner_model_name`
- `judge_feedback_trace`
- `replan_events`

Per-round additions:

- `plan_round_idx`
- `plan_version`
- `plan_goal`
- `plan_strategy`
- `judge_feedback`
- `followup_prompt`
- `followup_strategy`
- `followup_generator_model`
- `followup_generation_error`

This makes it possible to compare the initial chain with the executed sequence and inspect when the runtime changed course.

**Error Handling**

- Planner model missing from `models.yaml`: fail fast during startup.
- Planner returns invalid or empty plan: build a fallback plan and mark generation error in results.
- Judge returns invalid JSON: convert to a structured error feedback object and avoid replanning from it.
- Replanned suffix fails alignment checks: reject the replanned suffix and continue from the last valid plan.

**Testing Strategy**

- Unit test `AttackPlanner` initial six-round plan generation and fallback behavior.
- Unit test `LayeredJudge` structured `JudgeFeedback` parsing and malformed-output handling.
- Unit test runner state transitions, including replan triggers and plan-version recording.
- Unit test prompt generation remains anchored to `original_prompt` after judge feedback is applied.
- Extend CLI coverage to verify planner and judge models are resolved for the redesigned runtime.

**Files Expected To Change**

- `Jelly_Z/bin/jailbreak`
- `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- `Jailbreak/jailbreak_tools/multi_jail/runner.py`
- `Jailbreak/jailbreak_tools/multi_jail/prompt_strategy.py`
- `Jailbreak/jailbreak_tools/multi_jail/adaptive_strategy.py`
- `Jailbreak/jailbreak_tools/single_jail/judgers.py`
- `Jailbreak/jailbreak_tools/single_jail/model_tester.py`
- `tests/test_adaptive_multi_turn_strategy.py`
- `tests/test_multi_turn_judgers.py`
- `tests/test_multi_turn_runner.py`
