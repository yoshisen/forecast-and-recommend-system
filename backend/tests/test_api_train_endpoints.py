from __future__ import annotations

import importlib

import pytest


forecast_api = importlib.import_module("app.api.v1.forecast")
recommend_api = importlib.import_module("app.api.v1.recommend")
classification_api = importlib.import_module("app.api.v1.classification")
association_api = importlib.import_module("app.api.v1.association")
clustering_api = importlib.import_module("app.api.v1.clustering")
timeseries_api = importlib.import_module("app.api.v1.timeseries")


TRAIN_CASES = [
    ("/api/v1/forecast/train", forecast_api, "run_forecast_training", "訓練エラー"),
    ("/api/v1/recommend/train", recommend_api, "run_recommend_training", "訓練エラー"),
    (
        "/api/v1/classification/train",
        classification_api,
        "run_classification_training",
        "分類訓練エラー",
    ),
    (
        "/api/v1/association/train",
        association_api,
        "run_association_training",
        "関連ルール訓練エラー",
    ),
    (
        "/api/v1/clustering/train",
        clustering_api,
        "run_clustering_training",
        "クラスタリング訓練エラー",
    ),
    (
        "/api/v1/timeseries/train",
        timeseries_api,
        "run_prophet_training",
        "時系列訓練エラー",
    ),
]


@pytest.mark.parametrize("path,module,runner_name,expected_prefix", TRAIN_CASES)
def test_train_endpoint_without_uploaded_data_returns_404(
    client,
    path,
    module,
    runner_name,
    expected_prefix,
):
    del module, runner_name, expected_prefix
    response = client.post(path)
    assert response.status_code == 404
    assert "データが見つかりません" in response.json()["detail"]


@pytest.mark.parametrize("path,module,runner_name,expected_prefix", TRAIN_CASES)
def test_train_endpoint_success_returns_200(
    client,
    seeded_version,
    monkeypatch,
    path,
    module,
    runner_name,
    expected_prefix,
):
    del expected_prefix

    def fake_runner(_app, version_id):
        return {
            "ok": True,
            "version_id": version_id,
            "runner": runner_name,
        }

    monkeypatch.setattr(module, runner_name, fake_runner)

    response = client.post(path, params={"version": seeded_version})
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["metadata"]["version"] == seeded_version
    assert payload["data"]["ok"] is True
    assert payload["data"]["runner"] == runner_name


@pytest.mark.parametrize("path,module,runner_name,error_prefix", TRAIN_CASES)
def test_train_endpoint_runner_error_returns_500(
    client,
    seeded_version,
    monkeypatch,
    path,
    module,
    runner_name,
    error_prefix,
):
    def fake_runner(_app, _version_id):
        return {"error": "boom"}

    monkeypatch.setattr(module, runner_name, fake_runner)

    response = client.post(path, params={"version": seeded_version})
    assert response.status_code == 500
    assert error_prefix in response.json()["detail"]


def test_clustering_train_applies_requested_n_clusters(
    client,
    seeded_version,
    monkeypatch,
):
    class FakeClusterer:
        def __init__(self):
            self.last_n_clusters = None

        def fit(self, _parsed_data, n_clusters=4):
            self.last_n_clusters = n_clusters
            return {
                "n_clusters": n_clusters,
                "retrained": True,
            }

    fake_clusterer = FakeClusterer()

    def fake_run_clustering_training(app, _version_id):
        app.state.clusterer = fake_clusterer
        return {
            "summary": {
                "n_clusters": 4,
                "retrained": False,
            }
        }

    monkeypatch.setattr(clustering_api, "run_clustering_training", fake_run_clustering_training)

    response = client.post(
        "/api/v1/clustering/train",
        params={
            "version": seeded_version,
            "n_clusters": 7,
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["summary"]["n_clusters"] == 7
    assert payload["data"]["summary"]["retrained"] is True
    assert fake_clusterer.last_n_clusters == 7