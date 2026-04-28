"""Task readiness and training state registry."""
from __future__ import annotations

from typing import Dict, List, Any
from datetime import datetime

TASK_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "forecast": {
        "display_name": "Sales Forecast",
        "required_sheets": ["transaction_items", "transaction", "product"],
        "optional_sheets": ["store", "promotion", "weather", "holiday", "inventory"],
        "implemented": True,
    },
    "recommend": {
        "display_name": "Recommendation",
        "required_sheets": ["transaction_items", "transaction", "customer", "product"],
        "optional_sheets": ["customer_behavior"],
        "implemented": True,
    },
    "classification": {
        "display_name": "Classification",
        "required_sheets": ["transaction_items", "transaction", "customer"],
        "optional_sheets": ["customer_behavior"],
        "implemented": True,
    },
    "association": {
        "display_name": "Association Rules",
        "required_sheets": ["transaction_items", "transaction", "product"],
        "optional_sheets": ["customer"],
        "implemented": True,
    },
    "clustering": {
        "display_name": "Clustering",
        "required_sheets": ["transaction_items", "transaction", "customer"],
        "optional_sheets": ["store", "customer_behavior"],
        "implemented": True,
    },
    "prophet": {
        "display_name": "Prophet Time Series",
        "required_sheets": ["transaction_items", "transaction", "product"],
        "optional_sheets": ["holiday", "weather"],
        "implemented": True,
    },
}


def _build_reason_fields(missing_required: list[str], implemented: bool) -> tuple[str, str | None, str]:
    """不足状態から理由コード・互換理由・日本語理由を構築する。"""
    if missing_required:
        detail = ", ".join(missing_required)
        return (
            "missing_required_sheets",
            f"missing_required_sheets: {detail}",
            f"必須シート不足: {detail}",
        )

    if not implemented:
        return (
            "task_not_implemented_yet",
            "task_not_implemented_yet",
            "このタスクは未実装です",
        )

    return ("ok", None, "問題ありません")


def build_task_readiness(available_sheets: List[str]) -> Dict[str, Dict[str, Any]]:
    """Build a readiness matrix from available sheets."""
    available_set = set(available_sheets)
    matrix: Dict[str, Dict[str, Any]] = {}

    for task_name, config in TASK_DEFINITIONS.items():
        required = config.get("required_sheets", [])
        optional = config.get("optional_sheets", [])
        implemented = bool(config.get("implemented", False))

        missing_required = sorted([sheet for sheet in required if sheet not in available_set])
        missing_optional = sorted([sheet for sheet in optional if sheet not in available_set])
        data_ready = len(missing_required) == 0
        can_train = data_ready and implemented

        reason_code, reason, reason_ja = _build_reason_fields(
            missing_required=missing_required,
            implemented=implemented,
        )

        matrix[task_name] = {
            "display_name": config.get("display_name", task_name),
            "required_sheets": required,
            "optional_sheets": optional,
            "missing_required_sheets": missing_required,
            "missing_optional_sheets": missing_optional,
            "data_ready": data_ready,
            "implemented": implemented,
            "can_train": can_train,
            "reason_code": reason_code,
            "reason": reason,
            "reason_ja": reason_ja,
        }

    return matrix


def build_initial_training_state(readiness: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Create default training state for all known tasks."""
    timestamp = datetime.now().isoformat()
    state: Dict[str, Any] = {}

    for task_name, task_state in readiness.items():
        if task_state.get("can_train"):
            status = "pending"
            reason = None
            reason_code = None
            reason_ja = None
        else:
            status = "skipped"
            reason = task_state.get("reason") or "not_trainable"
            reason_code = task_state.get("reason_code") or "not_trainable"
            reason_ja = task_state.get("reason_ja") or "現在は学習できません"

        state[task_name] = status
        state[f"{task_name}_progress"] = 0
        state[f"{task_name}_reason"] = reason
        state[f"{task_name}_reason_code"] = reason_code
        state[f"{task_name}_reason_ja"] = reason_ja
        state[f"{task_name}_started_at"] = None
        state[f"{task_name}_finished_at"] = timestamp if status == "skipped" else None

    return state


def list_trainable_tasks(readiness: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return task names that are trainable with current data and implementation."""
    return [name for name, task_state in readiness.items() if task_state.get("can_train")]
