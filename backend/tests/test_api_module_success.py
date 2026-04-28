from __future__ import annotations


class FakeRecommender:
    def recommend(self, customer_id, top_k):
        return [
            {
                "product_id": "P000001",
                "product_name": "Milk",
                "category": "Dairy",
                "price": 120.0,
                "score": 0.91,
                "for_customer": customer_id,
            }
        ][:top_k]

    def recommend_popular(self, top_k, store_id=None):
        return [
            {
                "product_id": "P000002",
                "product_name": "Bread",
                "category": "Bakery",
                "price": 200.0,
                "score": 0.87,
                "store_id": store_id,
            }
        ][:top_k]


class FakeClassifier:
    def __init__(self):
        self.threshold = 0.5

    def predict_customer(self, customer_id, threshold=None):
        t = self.threshold if threshold is None else threshold
        return {
            "customer_id": customer_id,
            "prediction": 1,
            "probability": 0.88,
            "threshold": t,
        }

    def predict_with_features(self, body, threshold=None):
        t = self.threshold if threshold is None else threshold
        return {
            "prediction": 0,
            "probability": 0.21,
            "threshold": t,
            "input": body,
        }

    def scan_thresholds(self, step=0.05):
        return {
            "rows": [
                {
                    "threshold": round(step * 10, 2),
                    "precision": 0.8,
                    "recall": 0.7,
                    "f1": 0.7467,
                    "positive_predictions": 12,
                }
            ],
            "best_by_f1": {"threshold": 0.5, "f1": 0.7467},
        }

    def set_threshold(self, threshold):
        self.threshold = threshold


class FakeAssociationMiner:
    def __init__(self):
        self.summary = {"n_rules": 1}

    def list_rules(self, top_k=50):
        return [
            {
                "antecedents": ["P000001"],
                "consequents": ["P000002"],
                "support": 0.12,
                "confidence": 0.41,
                "lift": 1.34,
            }
        ][:top_k]

    def recommend(self, product_id, top_k=10):
        return [
            {
                "product_id": "P000002",
                "source_product_id": product_id,
                "confidence": 0.41,
                "lift": 1.34,
                "support": 0.12,
            }
        ][:top_k]


class FakeClusterer:
    def __init__(self):
        self.summary = {"n_clusters": 2}

    def get_segments(self):
        return [
            {"cluster": 0, "count": 2, "profile": {"transaction_count": 3.0}},
            {"cluster": 1, "count": 1, "profile": {"transaction_count": 1.0}},
        ]

    def get_points(self, limit=1500):
        points = [
            {"customer_id": "C000001", "cluster": 0, "pca_x": 0.1, "pca_y": 0.2},
            {"customer_id": "C000002", "cluster": 1, "pca_x": -0.2, "pca_y": 0.4},
        ]
        return points[: max(0, min(limit, len(points)))]

    def get_customer_cluster(self, customer_id):
        return {
            "customer_id": customer_id,
            "cluster": 0,
            "pca_x": 0.1,
            "pca_y": 0.2,
        }


class FakeProphetForecaster:
    def forecast(self, horizon=14):
        dates = [f"2026-01-{i + 1:02d}" for i in range(horizon)]
        return {
            "dates": dates,
            "yhat": [1.0] * horizon,
            "yhat_upper": [1.2] * horizon,
            "yhat_lower": [0.8] * horizon,
            "trend": [1.0] * horizon,
        }


def test_recommend_happy_path_returns_api_response(client, seeded_version):
    client.app.state.recommender = FakeRecommender()

    response = client.get(
        "/api/v1/recommend",
        params={"customer_id": "C000001", "top_k": 1, "version": seeded_version},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["customer_id"] == "C000001"
    assert payload["data"]["method"] == "hybrid"
    assert payload["data"]["count"] == len(payload["data"]["recommendations"])


def test_recommend_popular_happy_path_returns_api_response(client, seeded_version):
    client.app.state.recommender = FakeRecommender()

    response = client.get(
        "/api/v1/recommend/popular",
        params={"top_k": 1, "store_id": "S000001", "version": seeded_version},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["method"] == "popular"
    assert payload["data"]["store_id"] == "S000001"


def test_classification_predict_and_scan_happy_path(client, seeded_version):
    client.app.state.classifier = FakeClassifier()

    predict_response = client.get(
        "/api/v1/classification/predict",
        params={"customer_id": "C000001", "threshold": 0.6, "version": seeded_version},
    )
    assert predict_response.status_code == 200
    predict_payload = predict_response.json()
    assert predict_payload["success"] is True
    assert predict_payload["data"]["customer_id"] == "C000001"
    assert predict_payload["data"]["threshold"] == 0.6

    scan_response = client.get(
        "/api/v1/classification/threshold-scan",
        params={"step": 0.05, "version": seeded_version},
    )
    assert scan_response.status_code == 200
    scan_payload = scan_response.json()
    assert scan_payload["success"] is True
    assert len(scan_payload["data"]["rows"]) >= 1
    assert scan_payload["data"]["best_by_f1"]["threshold"] == 0.5


def test_classification_tune_threshold_happy_path(client, seeded_version):
    client.app.state.classifier = FakeClassifier()

    response = client.post(
        "/api/v1/classification/tune-threshold",
        params={"threshold": 0.65, "version": seeded_version},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["threshold"] == 0.65
    assert payload["data"]["best_by_f1"]["threshold"] == 0.5


def test_association_rules_and_recommendations_happy_path(client, seeded_version):
    client.app.state.association_miner = FakeAssociationMiner()

    rules_response = client.get(
        "/api/v1/association/rules",
        params={"top_k": 10, "version": seeded_version},
    )
    assert rules_response.status_code == 200
    rules_payload = rules_response.json()
    assert rules_payload["success"] is True
    assert rules_payload["data"]["count"] == 1
    assert "summary" in rules_payload["data"]

    rec_response = client.get(
        "/api/v1/association/recommendations",
        params={"product_id": "P000001", "top_k": 10, "version": seeded_version},
    )
    assert rec_response.status_code == 200
    rec_payload = rec_response.json()
    assert rec_payload["success"] is True
    assert rec_payload["data"]["product_id"] == "P000001"


def test_clustering_get_endpoints_happy_path(client, seeded_version):
    client.app.state.clusterer = FakeClusterer()

    segments_response = client.get(
        "/api/v1/clustering/segments",
        params={"version": seeded_version},
    )
    assert segments_response.status_code == 200
    segments_payload = segments_response.json()
    assert segments_payload["success"] is True
    assert segments_payload["data"]["count"] >= 1

    points_response = client.get(
        "/api/v1/clustering/points",
        params={"limit": 100, "version": seeded_version},
    )
    assert points_response.status_code == 200
    points_payload = points_response.json()
    assert points_payload["success"] is True
    assert points_payload["data"]["count"] >= 1

    customer_response = client.get(
        "/api/v1/clustering/customer/C000001",
        params={"version": seeded_version},
    )
    assert customer_response.status_code == 200
    customer_payload = customer_response.json()
    assert customer_payload["success"] is True
    assert customer_payload["data"]["customer_id"] == "C000001"


def test_timeseries_forecast_happy_path(client, seeded_version):
    client.app.state.prophet_forecaster = FakeProphetForecaster()

    response = client.get(
        "/api/v1/timeseries/forecast",
        params={"horizon": 3, "version": seeded_version},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert len(payload["data"]["dates"]) == 3
    assert len(payload["data"]["yhat"]) == 3