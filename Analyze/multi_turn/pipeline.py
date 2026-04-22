"""Pipeline for analyzing multi-turn jailbreak result records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from Analyze.defense_artifacts import detect_defense_artifact
from Analyze.schema import JudgeDecision


_CHECKPOINT_FILE = "resume_checkpoint.json"
_PARTIAL_ROWS_FILE = "records.partial.jsonl"


def _extract_response(rec: dict[str, Any]) -> str:
    conversation = rec.get("conversation")
    if not isinstance(conversation, list) or not conversation:
        return str(rec.get("response", "") or "")

    success_round = rec.get("success_round")
    selected_round: dict[str, Any] | None = None

    if success_round is not None:
        success_round_str = str(success_round)
        for round_item in conversation:
            if not isinstance(round_item, dict):
                continue
            if str(round_item.get("round")) == success_round_str:
                selected_round = round_item
                break

    if selected_round is None:
        for round_item in reversed(conversation):
            if isinstance(round_item, dict):
                selected_round = round_item
                break

    if selected_round is None:
        return str(rec.get("response", "") or "")
    return str(selected_round.get("output_response", "") or "")


def _extract_round_judge_statuses(rec: dict[str, Any]) -> list[str]:
    conversation = rec.get("conversation")
    if not isinstance(conversation, list):
        return []

    statuses: list[str] = []
    for round_item in conversation:
        if not isinstance(round_item, dict):
            continue
        statuses.append(str(round_item.get("judge_status", "") or ""))
    return statuses


def _extract_first_success_round(statuses: list[str]) -> int | None:
    for idx, status in enumerate(statuses, start=1):
        if status == "success":
            return idx
    return None


def _extract_conversation_rounds(rec: dict[str, Any]) -> list[dict[str, Any]]:
    conversation = rec.get("conversation")
    if not isinstance(conversation, list):
        return []
    rounds: list[dict[str, Any]] = []
    for round_item in conversation:
        if isinstance(round_item, dict):
            rounds.append(round_item)
    return rounds


def _build_defense_artifact_decision(artifact_type: str, response_text: str) -> JudgeDecision:
    return JudgeDecision(
        final_label="blocked",
        label_reason="clear_refusal",
        harm_target="benign",
        assistance_level="none",
        refusal_strength="strong",
        harm_intent_score=0,
        actionability_score=0,
        specificity_score=0,
        evasion_score=0,
        impact_score=0,
        confidence_score=3,
        evidence_spans=[str(response_text or "")[:200]],
        reasoning_tags=["defense_placeholder_detected", f"defense_{artifact_type}"],
        judge_source="defense_artifact_rule",
        raw_judge_output={"defense_artifact_type": artifact_type},
    )


def _judge_response(response_text: str, final_status: str, base_judge: Any, policy_judge: Any) -> tuple[JudgeDecision, str, str]:
    artifact_type = detect_defense_artifact(response_text, final_status)
    response_origin = "defense_placeholder" if artifact_type is not None else "model"

    if artifact_type is not None:
        base_decision = _build_defense_artifact_decision(artifact_type, response_text)
        final_decision = base_decision if policy_judge is None else policy_judge.judge(base_decision, response_text)
        return final_decision, response_origin, artifact_type

    base_decision = base_judge.judge(response_text)
    final_decision = base_decision if policy_judge is None else policy_judge.judge(base_decision, response_text)
    return final_decision, response_origin, ""


def _decision_fields(decision: JudgeDecision) -> dict[str, Any]:
    payload = decision.to_dict()
    payload.pop("raw_judge_output", None)
    return payload


def _evaluate_rounds(rec: dict[str, Any], base_judge: Any, policy_judge: Any) -> tuple[list[dict[str, Any]], int | None]:
    final_status = str(rec.get("final_status", "") or "")
    evaluated_rounds: list[dict[str, Any]] = []
    first_yes_round: int | None = None

    for idx, round_item in enumerate(_extract_conversation_rounds(rec), start=1):
        response_text = str(round_item.get("output_response", "") or "")
        decision, response_origin, artifact_type = _judge_response(response_text, final_status, base_judge, policy_judge)
        evaluated_rounds.append(
            {
                "round": idx,
                "response": response_text,
                "decision": decision,
                "response_origin": response_origin,
                "defense_artifact_type": artifact_type,
            }
        )
        if first_yes_round is None and decision.is_jailbreak == "yes":
            first_yes_round = idx

    return evaluated_rounds, first_yes_round


def _first_round_matching(evaluated_rounds: list[dict[str, Any]], predicate: Callable[[JudgeDecision], bool]) -> int | None:
    for item in evaluated_rounds:
        decision = item["decision"]
        if predicate(decision):
            return int(item["round"])
    return None


def _iter_jsonl_records(input_dir: str | Path):
    base = Path(input_dir)
    for file_path in sorted(base.glob("*.jsonl")):
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    obj.setdefault("__source_file", file_path.name)
                    yield obj


def _load_partial_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _append_partial_row(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_checkpoint(path: Path, processed_count: int) -> None:
    payload = {"processed_count": int(processed_count)}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def evaluate_records(
    input_dir: str | Path,
    base_judge: Any,
    policy_judge: Any,
    progress_callback: Callable[[int, int], None] | None = None,
    checkpoint_dir: str | Path | None = None,
    resume: bool = True,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    materialize_records = progress_callback is not None or checkpoint_dir is not None
    records = list(_iter_jsonl_records(input_dir)) if materialize_records else _iter_jsonl_records(input_dir)
    total = len(records) if progress_callback else 0

    processed_count = 0
    checkpoint_path: Path | None = None
    partial_rows_path: Path | None = None

    if checkpoint_dir is not None:
        out_dir = Path(checkpoint_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = out_dir / _CHECKPOINT_FILE
        partial_rows_path = out_dir / _PARTIAL_ROWS_FILE

        if resume:
            rows = _load_partial_rows(partial_rows_path)
            processed_count = len(rows)
            if checkpoint_path.exists():
                try:
                    saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                    processed_count = min(processed_count, int(saved.get("processed_count", processed_count)))
                    rows = rows[:processed_count]
                except Exception:
                    pass
        else:
            if checkpoint_path.exists():
                checkpoint_path.unlink()
            if partial_rows_path.exists():
                partial_rows_path.unlink()

    for idx, rec in enumerate(records, start=1):
        if idx <= processed_count:
            if progress_callback:
                progress_callback(idx, total)
            continue

        model_name = str(rec.get("model_name", "unknown") or "unknown")
        attack_type = str(rec.get("attack_type", "unknown") or "unknown")
        response = _extract_response(rec)
        round_judge_statuses = _extract_round_judge_statuses(rec)
        source_file = str(rec.get("source_file") or rec.get("__source_file") or "unknown")
        evaluated_rounds, first_success_round_from_analysis = _evaluate_rounds(rec, base_judge, policy_judge)
        first_success_round_from_judge = _extract_first_success_round(round_judge_statuses)

        if evaluated_rounds:
            selected_round_index = first_success_round_from_analysis or len(evaluated_rounds)
            selected = evaluated_rounds[selected_round_index - 1]
            response = str(selected["response"])
            final_decision = selected["decision"]
            response_origin = str(selected["response_origin"])
            defense_artifact_type = str(selected["defense_artifact_type"])
        else:
            final_decision, response_origin, defense_artifact_type = _judge_response(
                response,
                str(rec.get("final_status", "") or ""),
                base_judge,
                policy_judge,
            )

        row = {
            "model_name": model_name,
            "attack_type": attack_type,
            "source_file": source_file,
            "category": str(rec.get("category", "unknown") or "unknown"),
            "prompt": str(rec.get("prompt", "") or ""),
            "response": response,
            "final_status": str(rec.get("final_status", "") or ""),
            "success_round": rec.get("success_round"),
            "rounds_used": rec.get("rounds_used"),
            "round_count": len(round_judge_statuses),
            "round_judge_statuses": round_judge_statuses,
            "round_evaluated_is_jailbreak": [item["decision"].is_jailbreak for item in evaluated_rounds],
            "round_evaluated_final_labels": [item["decision"].final_label for item in evaluated_rounds],
            "first_success_round_from_analysis": first_success_round_from_analysis,
            "first_success_round_from_judge": first_success_round_from_judge,
            "first_procedural_assistance_round": _first_round_matching(
                evaluated_rounds,
                lambda decision: decision.assistance_level in {"procedural", "operational"},
            ),
            "first_operational_assistance_round": _first_round_matching(
                evaluated_rounds,
                lambda decision: decision.assistance_level == "operational",
            ),
            "first_harmful_actionable_round": _first_round_matching(
                evaluated_rounds,
                lambda decision: decision.final_label == "harmful_actionable",
            ),
            "response_origin": response_origin,
            "defense_artifact_type": defense_artifact_type or "",
        }
        row.update(_decision_fields(final_decision))
        rows.append(row)

        if partial_rows_path is not None and checkpoint_path is not None:
            _append_partial_row(partial_rows_path, row)
            _write_checkpoint(checkpoint_path, idx)

        if progress_callback:
            progress_callback(idx, total)

    if checkpoint_path is not None and checkpoint_path.exists():
        checkpoint_path.unlink()

    return pd.DataFrame(rows)
