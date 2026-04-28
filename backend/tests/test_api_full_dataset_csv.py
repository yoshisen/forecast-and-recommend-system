from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path

import pandas as pd
import pytest


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "schema_v2_full"
SHEET_NAMES = [
    "transaction",
    "transaction_items",
    "product",
    "customer",
    "store",
    "promotion",
    "inventory",
    "weather",
    "holiday",
    "customer_behavior",
    "product_association",
    "review",
]
HAS_PROPHET = importlib.util.find_spec("prophet") is not None


def _load_schema_v2_parsed_data() -> dict[str, pd.DataFrame]:
    parsed_data: dict[str, pd.DataFrame] = {}
    for sheet_name in SHEET_NAMES:
        parsed_data[sheet_name] = pd.read_csv(FIXTURE_DIR / f"{sheet_name}.csv")
    return parsed_data


@pytest.fixture(name="seeded_version_schema_v2")
def _seeded_version_schema_v2(client):
    version_id = "schema_v2_full_csv"
    parsed_data = _load_schema_v2_parsed_data()

    client.app.state.data_versions[version_id] = {
        "parsed_data": parsed_data,
        "parse_report": {
            "identified_sheets": sorted(parsed_data.keys()),
            "total_sheets": len(parsed_data),
        },
        "quality_report": {
            "overall_summary": {
                "total_sheets": len(parsed_data),
                "total_rows": int(sum(len(df) for df in parsed_data.values())),
                "total_fields": int(sum(len(df.columns) for df in parsed_data.values())),
            },
            "sheet_reports": {},
        },
        "validation_result": {},
        "uploaded_at": datetime.now().isoformat(),
        "filename": "schema_v2_full_upload.xlsx",
        "training": {},
        "task_readiness": {},
    }
    client.app.state.current_version = version_id

    return version_id


def test_schema_v2_csv_field_readiness_all_tasks_trainable(client, request):
    version = request.getfixturevalue("seeded_version_schema_v2")

    response = client.get(
        "/api/v1/data/field-readiness",
        params={"version": version},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True

    readiness = payload["data"]["field_readiness"]

    assert readiness["summary"]["task_total_count"] == 6
    assert readiness["summary"]["task_trainable_count"] == 6

    for task_name, task_info in readiness["tasks"].items():
        assert task_info["can_train_with_fields"] is True, f"{task_name} blocked: {task_info}"


def test_schema_v2_csv_train_and_predict_core_endpoints(client, request):
    version = request.getfixturevalue("seeded_version_schema_v2")

    train_endpoints = [
        "/api/v1/forecast/train",
        "/api/v1/recommend/train",
        "/api/v1/classification/train",
        "/api/v1/association/train",
        "/api/v1/clustering/train",
    ]

    for path in train_endpoints:
        response = client.post(path, params={"version": version})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["success"] is True

    forecast_response = client.get(
        "/api/v1/forecast",
        params={
            "product_id": "P000001",
            "store_id": "S000001",
            "horizon": 7,
            "version": version,
        },
    )
    assert forecast_response.status_code == 200, forecast_response.text
    forecast_payload = forecast_response.json()
    assert forecast_payload["success"] is True
    assert len(forecast_payload["data"]["predictions"]) == 7

    recommend_response = client.get(
        "/api/v1/recommend",
        params={
            "customer_id": "C000001",
            "top_k": 5,
            "version": version,
        },
    )
    assert recommend_response.status_code == 200, recommend_response.text
    recommend_payload = recommend_response.json()
    assert recommend_payload["success"] is True
    assert recommend_payload["data"]["count"] >= 1

    popular_response = client.get(
        "/api/v1/recommend/popular",
        params={
            "top_k": 5,
            "store_id": "S000001",
            "version": version,
        },
    )
    assert popular_response.status_code == 200, popular_response.text
    assert popular_response.json()["success"] is True

    class_predict_response = client.get(
        "/api/v1/classification/predict",
        params={
            "customer_id": "C000001",
            "version": version,
        },
    )
    assert class_predict_response.status_code == 200, class_predict_response.text
    class_predict_payload = class_predict_response.json()
    assert class_predict_payload["success"] is True
    assert "probability" in class_predict_payload["data"]

    class_scan_response = client.get(
        "/api/v1/classification/threshold-scan",
        params={
            "step": 0.05,
            "version": version,
        },
    )
    assert class_scan_response.status_code == 200, class_scan_response.text
    class_scan_payload = class_scan_response.json()
    assert class_scan_payload["success"] is True
    assert len(class_scan_payload["data"]["rows"]) > 0

    association_rules_response = client.get(
        "/api/v1/association/rules",
        params={
            "top_k": 20,
            "version": version,
        },
    )
    assert association_rules_response.status_code == 200, association_rules_response.text
    association_rules_payload = association_rules_response.json()
    assert association_rules_payload["success"] is True
    assert association_rules_payload["data"]["count"] >= 1

    association_rec_response = client.get(
        "/api/v1/association/recommendations",
        params={
            "product_id": "P000001",
            "top_k": 10,
            "version": version,
        },
    )
    assert association_rec_response.status_code == 200, association_rec_response.text
    association_rec_payload = association_rec_response.json()
    assert association_rec_payload["success"] is True

    clustering_segments_response = client.get(
        "/api/v1/clustering/segments",
        params={"version": version},
    )
    assert clustering_segments_response.status_code == 200, clustering_segments_response.text
    clustering_segments_payload = clustering_segments_response.json()
    assert clustering_segments_payload["success"] is True
    assert clustering_segments_payload["data"]["count"] >= 2

    clustering_points_response = client.get(
        "/api/v1/clustering/points",
        params={"limit": 100, "version": version},
    )
    assert clustering_points_response.status_code == 200, clustering_points_response.text
    clustering_points_payload = clustering_points_response.json()
    assert clustering_points_payload["success"] is True
    assert clustering_points_payload["data"]["count"] >= 1

    clustering_customer_response = client.get(
        "/api/v1/clustering/customer/C000001",
        params={"version": version},
    )
    assert clustering_customer_response.status_code == 200, clustering_customer_response.text
    clustering_customer_payload = clustering_customer_response.json()
    assert clustering_customer_payload["success"] is True
    assert clustering_customer_payload["data"]["customer_id"] == "C000001"


def test_schema_v2_csv_forecast_supports_algorithm_selection(client, request):
    version = request.getfixturevalue("seeded_version_schema_v2")

    train_response = client.post(
        "/api/v1/forecast/train",
        params={"version": version},
    )
    assert train_response.status_code == 200, train_response.text
    assert train_response.json()["success"] is True

    for algorithm in ["lightgbm", "xgboost", "sarima"]:
        response = client.get(
            "/api/v1/forecast",
            params={
                "product_id": "P000001",
                "store_id": "S000001",
                "horizon": 7,
                "algorithm": algorithm,
                "version": version,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["requested_algorithm"] == algorithm
        assert len(payload["data"]["predictions"]) == 7


@pytest.mark.skipif(not HAS_PROPHET, reason="prophet package is not installed")
def test_schema_v2_csv_timeseries_train_and_forecast(client, request):
    version = request.getfixturevalue("seeded_version_schema_v2")

    train_response = client.post(
        "/api/v1/timeseries/train",
        params={"version": version},
    )
    assert train_response.status_code == 200, train_response.text
    train_payload = train_response.json()
    assert train_payload["success"] is True

    forecast_response = client.get(
        "/api/v1/timeseries/forecast",
        params={
            "horizon": 7,
            "version": version,
        },
    )
    assert forecast_response.status_code == 200, forecast_response.text
    forecast_payload = forecast_response.json()
    assert forecast_payload["success"] is True
    assert len(forecast_payload["data"]["dates"]) == 7
