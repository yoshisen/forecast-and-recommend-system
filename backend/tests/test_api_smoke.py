from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "healthy"
    assert "timestamp" in payload


def test_versions_initially_empty(client):
    response = client.get("/api/v1/versions")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["versions"] == []
    assert payload["data"]["current_version"] is None


def test_summary_without_upload_returns_404(client):
    response = client.get("/api/v1/data/summary")
    assert response.status_code == 404
    assert "データが見つかりません" in response.json()["detail"]


def test_forecast_without_trained_model_returns_400(client, seeded_version):
    response = client.get(
        "/api/v1/forecast",
        params={
            "product_id": "P000001",
            "store_id": "S000001",
            "version": seeded_version,
        },
    )
    assert response.status_code == 400
    assert "訓練されていません" in response.json()["detail"]


def test_upload_schema_endpoint_returns_expected_structure(client):
    response = client.get("/api/v1/data/upload-schema")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert "data" in payload

    data = payload["data"]
    assert "sheets" in data
    assert "field_catalog" in data
    assert "task_requirements" in data

    sheet_names = [item["sheet"] for item in data["sheets"]]
    assert "transaction_items" in sheet_names

    field_names = [item["field"] for item in data["field_catalog"]]
    assert "transaction_id" in field_names


def test_field_readiness_endpoint_returns_expected_structure(client, seeded_version):
    response = client.get(
        "/api/v1/data/field-readiness",
        params={"version": seeded_version},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert "data" in payload

    data = payload["data"]
    assert data["version"] == seeded_version
    assert "field_readiness" in data
    assert "tasks" in data["field_readiness"]
    assert "forecast" in data["field_readiness"]["tasks"]

    forecast_info = data["field_readiness"]["tasks"]["forecast"]
    assert "reason_code" in forecast_info
    assert "reason_ja" in forecast_info