from __future__ import annotations

import importlib

import pandas as pd


data_api = importlib.import_module("app.api.v1.data")


def _build_parsed_data_for_warning_test() -> dict[str, pd.DataFrame]:
    return {
        "transaction_items": pd.DataFrame([
            {"transaction_id": "T0001", "product_id": "P0001"}
        ]),
        "transaction": pd.DataFrame([
            {"transaction_id": "T0001"}
        ]),
        "product": pd.DataFrame([
            {"product_id": "P0001"}
        ]),
    }


def test_upload_warnings_include_reason_metadata(client, monkeypatch, tmp_path):
    parsed_data = _build_parsed_data_for_warning_test()

    class FakeExcelParser:
        def __init__(self, _upload_path):
            self.upload_path = _upload_path

        def parse(self):
            return {
                "success": True,
                "parsed_data": parsed_data,
                "report": {"sheet_count": len(parsed_data)},
            }

    class FakeDataQualityChecker:
        def __init__(self, parsed_data_input):
            self.parsed_data_input = parsed_data_input

        def generate_report(self):
            return {
                "overall_summary": {
                    "total_sheets": len(self.parsed_data_input),
                    "total_rows": sum(len(df) for df in self.parsed_data_input.values()),
                    "total_fields": sum(len(df.columns) for df in self.parsed_data_input.values()),
                },
                "sheet_reports": {
                    sheet_name: {
                        "row_count": len(df),
                        "column_count": len(df.columns),
                        "data_range": {},
                    }
                    for sheet_name, df in self.parsed_data_input.items()
                },
            }

    class FakeDataValidator:
        @staticmethod
        def validate_relationships(_parsed_data):
            return {"is_valid": True, "errors": []}

    def _noop_training(_app, _version_id):
        return {"ok": True}

    monkeypatch.setattr(data_api, "ExcelParser", FakeExcelParser)
    monkeypatch.setattr(data_api, "DataQualityChecker", FakeDataQualityChecker)
    monkeypatch.setattr(data_api, "DataValidator", FakeDataValidator)
    monkeypatch.setattr(data_api.settings, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(data_api.settings, "DELETE_AFTER_PARSE", True)

    monkeypatch.setattr(data_api, "run_forecast_training", _noop_training)
    monkeypatch.setattr(data_api, "run_recommend_training", _noop_training)
    monkeypatch.setattr(data_api, "run_classification_training", _noop_training)
    monkeypatch.setattr(data_api, "run_association_training", _noop_training)
    monkeypatch.setattr(data_api, "run_clustering_training", _noop_training)
    monkeypatch.setattr(data_api, "run_prophet_training", _noop_training)

    response = client.post(
        "/api/v1/upload",
        files={
            "file": (
                "warning-test.xlsx",
                b"test-content",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200

    payload = response.json()
    warnings = payload["warnings"]
    assert len(warnings) > 0

    missing_sheet_warning = next(
        item
        for item in warnings
        if item.get("type") == "missing_required_sheet" and item.get("task") == "recommend"
    )
    assert missing_sheet_warning["reason_code"] == "missing_required_sheets"
    assert missing_sheet_warning["reason"] == "missing_required_sheets: customer"
    assert missing_sheet_warning["reason_ja"] == "必須シート不足: customer"

    missing_field_warning = next(
        item
        for item in warnings
        if item.get("type") == "missing_required_field" and item.get("task") == "forecast"
    )
    assert missing_field_warning["reason_code"] == "missing_required_fields"
    assert missing_field_warning["reason"] == "missing_required_fields: transaction[transaction_date]"
    assert missing_field_warning["reason_ja"] == "必須フィールド不足: transaction[transaction_date]"

    missing_optional_warning = next(
        item
        for item in warnings
        if item.get("type") == "missing_optional_sheet" and item.get("reason") == "missing_optional_sheet: promotion"
    )
    assert missing_optional_warning["reason_code"] == "missing_optional_sheet"
    assert missing_optional_warning["reason_ja"] == "任意シート不足: promotion"

    recommend_readiness = payload["task_readiness"]["recommend"]
    assert recommend_readiness["reason_code"] == "missing_required_sheets"
    assert recommend_readiness["reason"] == "missing_required_sheets: customer"
    assert recommend_readiness["reason_ja"] == "必須シート不足: customer"

    recommend_auto_training = payload["auto_training"]["recommend"]
    assert recommend_auto_training["reason_code"] == "missing_required_sheets"
    assert recommend_auto_training["reason"] == "missing_required_sheets: customer"
    assert recommend_auto_training["reason_ja"] == "必須シート不足: customer"

    forecast_auto_training = payload["auto_training"]["forecast"]
    assert forecast_auto_training["status"] == "skipped"
    assert forecast_auto_training["reason_code"] == "missing_required_fields"
    assert forecast_auto_training["reason"] == "missing_required_fields: transaction[transaction_date]"
    assert forecast_auto_training["reason_ja"] == "必須フィールド不足: transaction[transaction_date]"
