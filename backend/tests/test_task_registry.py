from __future__ import annotations

import importlib


task_registry_module = importlib.import_module("app.core.task_registry")
build_task_readiness = task_registry_module.build_task_readiness
build_initial_training_state = task_registry_module.build_initial_training_state


def test_readiness_all_required_sheets_trainable():
    available_sheets = [
        "transaction_items",
        "transaction",
        "product",
        "customer",
    ]

    readiness = build_task_readiness(available_sheets)

    assert readiness["forecast"]["can_train"] is True
    assert readiness["recommend"]["can_train"] is True
    assert readiness["classification"]["can_train"] is True
    assert readiness["association"]["can_train"] is True
    assert readiness["clustering"]["can_train"] is True
    assert readiness["prophet"]["can_train"] is True


def test_readiness_missing_customer_marks_related_tasks_untrainable():
    available_sheets = [
        "transaction_items",
        "transaction",
        "product",
    ]

    readiness = build_task_readiness(available_sheets)

    assert readiness["forecast"]["can_train"] is True
    assert readiness["association"]["can_train"] is True
    assert readiness["prophet"]["can_train"] is True

    assert readiness["recommend"]["can_train"] is False
    assert readiness["classification"]["can_train"] is False
    assert readiness["clustering"]["can_train"] is False
    assert "customer" in readiness["recommend"]["missing_required_sheets"]


def test_readiness_exposes_reason_metadata_for_missing_required_sheets():
    available_sheets = [
        "transaction_items",
        "transaction",
        "product",
    ]

    readiness = build_task_readiness(available_sheets)

    recommend_info = readiness["recommend"]
    assert recommend_info["reason_code"] == "missing_required_sheets"
    assert recommend_info["reason"] == "missing_required_sheets: customer"
    assert recommend_info["reason_ja"] == "必須シート不足: customer"

    forecast_info = readiness["forecast"]
    assert forecast_info["reason_code"] == "ok"
    assert forecast_info["reason"] is None
    assert forecast_info["reason_ja"] == "問題ありません"


def test_initial_training_state_keeps_reason_metadata_for_skipped_tasks():
    available_sheets = [
        "transaction_items",
        "transaction",
        "product",
    ]
    readiness = build_task_readiness(available_sheets)

    state = build_initial_training_state(readiness)

    assert state["recommend"] == "skipped"
    assert state["recommend_reason"] == "missing_required_sheets: customer"
    assert state["recommend_reason_code"] == "missing_required_sheets"
    assert state["recommend_reason_ja"] == "必須シート不足: customer"

    assert state["forecast"] == "pending"
    assert state["forecast_reason"] is None
    assert state["forecast_reason_code"] is None
    assert state["forecast_reason_ja"] is None