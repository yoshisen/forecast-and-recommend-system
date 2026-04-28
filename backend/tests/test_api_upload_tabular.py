from __future__ import annotations

import importlib
import io
import zipfile


data_api = importlib.import_module("app.api.v1.data")


def _disable_auto_training(monkeypatch):
    def _noop_train(*_args, **_kwargs):
        return {"status": "skipped_for_test"}

    monkeypatch.setattr(data_api, "run_forecast_training", _noop_train)
    monkeypatch.setattr(data_api, "run_recommend_training", _noop_train)
    monkeypatch.setattr(data_api, "run_classification_training", _noop_train)
    monkeypatch.setattr(data_api, "run_association_training", _noop_train)
    monkeypatch.setattr(data_api, "run_clustering_training", _noop_train)
    monkeypatch.setattr(data_api, "run_prophet_training", _noop_train)


def test_upload_single_csv_parses_sheet_successfully(client, monkeypatch, tmp_path):
    monkeypatch.setattr(data_api.settings, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(data_api.settings, "DELETE_AFTER_PARSE", True)
    _disable_auto_training(monkeypatch)

    csv_bytes = b"transaction_id,product_id,quantity\nT0001,P0001,2\nT0002,P0002,1\n"

    response = client.post(
        "/api/v1/upload",
        files={
            "file": (
                "transaction_items.csv",
                csv_bytes,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["metadata"]["filename"] == "transaction_items.csv"
    assert "transaction_items" in payload["parsed_data_summary"]["sheet_names"]
    assert payload["parse_report"]["source_format"] == "csv"
    assert payload["field_readiness"]["summary"]["task_trainable_count"] < 6

    missing_core_warning = next(
        item
        for item in payload["warnings"]
        if item.get("type") == "tabular_missing_core_sheets"
    )
    assert missing_core_warning["reason_code"] == "missing_required_sheets"


def test_upload_zip_with_multiple_csv_parses_recognized_sheets(client, monkeypatch, tmp_path):
    monkeypatch.setattr(data_api.settings, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(data_api.settings, "DELETE_AFTER_PARSE", True)
    _disable_auto_training(monkeypatch)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "transaction_items.csv",
            "transaction_id,product_id,quantity\nT0001,P0001,2\n",
        )
        archive.writestr(
            "product.csv",
            "product_id,product_name\nP0001,Milk\n",
        )
        archive.writestr(
            "unknown_sheet.csv",
            "a,b\n1,2\n",
        )

    response = client.post(
        "/api/v1/upload",
        files={
            "file": (
                "bundle.zip",
                zip_buffer.getvalue(),
                "application/zip",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    sheet_names = set(payload["parsed_data_summary"]["sheet_names"])
    assert {"transaction_items", "product"}.issubset(sheet_names)
    assert payload["parse_report"]["source_format"] == "zip"
    assert "unknown_sheet.csv" in payload["parse_report"]["skipped_files"]

    zip_skipped_warning = next(
        item
        for item in payload["warnings"]
        if item.get("type") == "zip_skipped_files"
    )
    assert "unknown_sheet.csv" in zip_skipped_warning["message"]
    assert "候補:" in zip_skipped_warning["impact"]
    assert "unknown_sheet.csv ->" in zip_skipped_warning["impact"]
    assert "unknown_sheet.csv" in zip_skipped_warning["suggested_sheet_names_by_file"]
    candidate_names = zip_skipped_warning["suggested_sheet_names_by_file"]["unknown_sheet.csv"]
    assert isinstance(candidate_names, list)
    assert len(candidate_names) > 0

    missing_core_warning = next(
        item
        for item in payload["warnings"]
        if item.get("type") == "tabular_missing_core_sheets"
    )
    assert missing_core_warning["reason_code"] == "missing_required_sheets"
    assert "CSV/ZIP" in missing_core_warning["message"]


def test_upload_csv_with_unknown_file_name_returns_400(client, monkeypatch, tmp_path):
    monkeypatch.setattr(data_api.settings, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(data_api.settings, "DELETE_AFTER_PARSE", True)
    _disable_auto_training(monkeypatch)

    csv_bytes = b"transaction_id,product_id,quantity\nT0001,P0001,2\n"

    response = client.post(
        "/api/v1/upload",
        files={
            "file": (
                "sales_dump.csv",
                csv_bytes,
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert "ファイル解析エラー" in response.json()["detail"]
    assert "候補:" in response.json()["detail"]
    assert "transaction_items" in response.json()["detail"]


def test_upload_csv_with_prefixed_and_suffixed_name_maps_longest_sheet(client, monkeypatch, tmp_path):
    monkeypatch.setattr(data_api.settings, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(data_api.settings, "DELETE_AFTER_PARSE", True)
    _disable_auto_training(monkeypatch)

    csv_bytes = (
        b"product_id_a,product_id_b,support,confidence,lift\n"
        b"P0001,P0002,0.12,0.44,1.28\n"
    )

    response = client.post(
        "/api/v1/upload",
        files={
            "file": (
                "2026Q2-product_association-export.csv",
                csv_bytes,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "product_association" in payload["parsed_data_summary"]["sheet_names"]
    assert "product" not in payload["parsed_data_summary"]["sheet_names"]


def test_upload_multiple_csv_single_request_covers_all_tasks(client, monkeypatch, tmp_path):
    monkeypatch.setattr(data_api.settings, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(data_api.settings, "DELETE_AFTER_PARSE", True)
    _disable_auto_training(monkeypatch)

    files = [
        (
            "files",
            (
                "transaction_items.csv",
                b"transaction_id,product_id,quantity\nT0001,P0001,2\nT0002,P0002,1\n",
                "text/csv",
            ),
        ),
        (
            "files",
            (
                "transaction.csv",
                b"transaction_id,customer_id,transaction_date,store_id\nT0001,C0001,2026-01-01,S0001\nT0002,C0002,2026-01-02,S0001\n",
                "text/csv",
            ),
        ),
        (
            "files",
            (
                "product.csv",
                b"product_id,product_name\nP0001,Milk\nP0002,Bread\n",
                "text/csv",
            ),
        ),
        (
            "files",
            (
                "customer.csv",
                b"customer_id,gender\nC0001,F\nC0002,M\n",
                "text/csv",
            ),
        ),
    ]

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["parse_report"]["source_format"] == "zip"
    assert payload["metadata"]["filename"] == "multi_csv_upload_4_files.zip"

    summary = payload["field_readiness"]["summary"]
    assert summary["task_total_count"] == 6
    assert summary["task_trainable_count"] == 6

    for task_name, info in payload["task_field_readiness"].items():
        assert info["can_train_with_fields"] is True, f"{task_name}: {info}"
