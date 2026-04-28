from __future__ import annotations


def test_recommend_without_trained_model_returns_400(client, seeded_version):
    response = client.get(
        "/api/v1/recommend",
        params={"customer_id": "C000001", "version": seeded_version},
    )
    assert response.status_code == 400
    assert "推薦モデルが訓練されていません" in response.json()["detail"]


def test_recommend_popular_without_trained_model_returns_400(client, seeded_version):
    response = client.get(
        "/api/v1/recommend/popular",
        params={"top_k": 10, "version": seeded_version},
    )
    assert response.status_code == 400
    assert "推薦モデルが訓練されていません" in response.json()["detail"]


def test_classification_predict_without_trained_model_returns_400(client, seeded_version):
    response = client.get(
        "/api/v1/classification/predict",
        params={"customer_id": "C000001", "version": seeded_version},
    )
    assert response.status_code == 400
    assert "分類モデルが訓練されていません" in response.json()["detail"]


def test_association_rules_without_trained_model_returns_400(client, seeded_version):
    response = client.get(
        "/api/v1/association/rules",
        params={"version": seeded_version},
    )
    assert response.status_code == 400
    assert "関連ルールモデルが訓練されていません" in response.json()["detail"]


def test_clustering_segments_without_trained_model_returns_400(client, seeded_version):
    response = client.get(
        "/api/v1/clustering/segments",
        params={"version": seeded_version},
    )
    assert response.status_code == 400
    assert "クラスタリングモデルが訓練されていません" in response.json()["detail"]


def test_timeseries_forecast_without_trained_model_returns_400(client, seeded_version):
    response = client.get(
        "/api/v1/timeseries/forecast",
        params={"version": seeded_version},
    )
    assert response.status_code == 400
    assert "Prophetモデルが訓練されていません" in response.json()["detail"]


def test_recommend_top_k_lower_bound_returns_422(client, seeded_version):
    response = client.get(
        "/api/v1/recommend",
        params={"customer_id": "C000001", "top_k": 0, "version": seeded_version},
    )
    assert response.status_code == 422


def test_classification_threshold_upper_bound_returns_422(client, seeded_version):
    response = client.get(
        "/api/v1/classification/predict",
        params={"customer_id": "C000001", "threshold": 1, "version": seeded_version},
    )
    assert response.status_code == 422


def test_classification_scan_step_lower_bound_returns_422(client, seeded_version):
    response = client.get(
        "/api/v1/classification/threshold-scan",
        params={"step": 0, "version": seeded_version},
    )
    assert response.status_code == 422


def test_association_top_k_upper_bound_returns_422(client, seeded_version):
    response = client.get(
        "/api/v1/association/recommendations",
        params={"product_id": "P000001", "top_k": 101, "version": seeded_version},
    )
    assert response.status_code == 422


def test_clustering_n_clusters_lower_bound_returns_422(client, seeded_version):
    response = client.post(
        "/api/v1/clustering/train",
        params={"n_clusters": 1, "version": seeded_version},
    )
    assert response.status_code == 422


def test_clustering_points_limit_lower_bound_returns_422(client, seeded_version):
    response = client.get(
        "/api/v1/clustering/points",
        params={"limit": 99, "version": seeded_version},
    )
    assert response.status_code == 422


def test_timeseries_horizon_lower_bound_returns_422(client, seeded_version):
    response = client.get(
        "/api/v1/timeseries/forecast",
        params={"horizon": 0, "version": seeded_version},
    )
    assert response.status_code == 422