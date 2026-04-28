"""Training events and progress broadcasting utilities."""
from typing import Any, Dict
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

PROGRESS_STAGES_FORECAST = [
    (5, "init"),
    (25, "feature_engine"),
    (40, "feature_done"),
    (50, "model_init"),
    (85, "model_train"),
    (95, "metrics"),
]

PROGRESS_STAGES_RECOMMEND = [
    (5, "init"),
    (20, "interaction_matrix"),
    (40, "product_features"),
    (55, "model_init"),
    (85, "model_train"),
    (95, "metrics"),
]

PROGRESS_STAGES_CLASSIFICATION = [
    (5, "init"),
    (35, "feature_engine"),
    (55, "model_init"),
    (88, "model_train"),
    (95, "metrics"),
]

PROGRESS_STAGES_ASSOCIATION = [
    (5, "init"),
    (35, "basket_build"),
    (75, "rule_mining"),
    (95, "summary"),
]

PROGRESS_STAGES_CLUSTERING = [
    (5, "init"),
    (30, "feature_engine"),
    (55, "model_init"),
    (85, "model_train"),
    (95, "profiles"),
]

PROGRESS_STAGES_PROPHET = [
    (5, "init"),
    (35, "daily_series"),
    (55, "model_init"),
    (85, "model_train"),
    (95, "metrics"),
]


def _ensure_ws_state(app):
    if not hasattr(app.state, "ws_clients"):
        app.state.ws_clients = set()


def _ensure_training_record(app, version_id: str) -> Dict[str, Any] | None:
    version_data = app.state.data_versions.get(version_id)
    if not version_data:
        return None
    tr = version_data.get("training")
    if tr is None:
        tr = {}
        version_data["training"] = tr
    return tr


def broadcast_training_update(app, payload: Dict[str, Any]):
    """Send a training update payload to all connected websocket clients."""
    _ensure_ws_state(app)
    dead = []
    for ws in app.state.ws_clients:
        try:
            asyncio.create_task(ws.send_json(payload))
        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            logger.warning("WebSocket send failed: %s", e)
            dead.append(ws)
    for d in dead:
        app.state.ws_clients.discard(d)


def _init_training_record(app, version_id: str, model: str, status: str = "running"):
    tr = _ensure_training_record(app, version_id)
    if tr is None:
        return

    tr[model] = status
    tr[f"{model}_progress"] = 0
    tr[f"{model}_reason"] = None
    tr[f"{model}_started_at"] = datetime.now().isoformat()
    tr[f"{model}_finished_at"] = None

    tr.pop(f"{model}_error", None)
    tr.pop(f"{model}_error_trace", None)
    tr.pop(f"{model}_metrics", None)
    tr.pop(f"{model}_matrix_info", None)
    tr.pop(f"{model}_summary", None)


def _update_progress(app, version_id: str, model: str, progress: int, stage: str):
    tr = _ensure_training_record(app, version_id)
    if tr is None:
        return

    tr[f"{model}_progress"] = int(progress)
    broadcast_training_update(
        app,
        {
            "type": "training_update",
            "model": model,
            "version": version_id,
            "status": tr.get(model),
            "progress": int(progress),
            "stage": stage,
            "metrics": tr.get(f"{model}_metrics"),
            "error": tr.get(f"{model}_error"),
            "reason": tr.get(f"{model}_reason"),
        },
    )


def _finalize(
    app,
    version_id: str,
    model: str,
    status: str,
    metrics: Dict[str, Any] | None = None,
    matrix_info: Dict[str, Any] | None = None,
    summary: Dict[str, Any] | None = None,
    error: str | None = None,
    error_trace: str | None = None,
):
    tr = _ensure_training_record(app, version_id)
    if tr is None:
        return

    tr[model] = status
    tr[f"{model}_finished_at"] = datetime.now().isoformat()

    if metrics:
        tr[f"{model}_metrics"] = metrics
    if matrix_info:
        tr[f"{model}_matrix_info"] = matrix_info
    if summary:
        tr[f"{model}_summary"] = summary
    if error:
        tr[f"{model}_error"] = error
        tr[f"{model}_reason"] = error
    if error_trace:
        tr[f"{model}_error_trace"] = error_trace

    if status == "failed":
        tr[f"{model}_progress"] = tr.get(f"{model}_progress", 0)
    else:
        tr[f"{model}_progress"] = 100

    broadcast_training_update(
        app,
        {
            "type": "training_update",
            "model": model,
            "version": version_id,
            "status": status,
            "progress": tr.get(f"{model}_progress", 0),
            "stage": "complete" if status == "completed" else "error",
            "metrics": tr.get(f"{model}_metrics"),
            "error": tr.get(f"{model}_error"),
            "reason": tr.get(f"{model}_reason"),
        },
    )


def run_forecast_training(app, version_id: str):
    from app.core.feature_engine import FeatureEngine
    from app.models.forecasting import ForecastingPipeline

    version_data = app.state.data_versions.get(version_id)
    if not version_data:
        return {"error": "version_not_found"}

    parsed = version_data["parsed_data"]
    _init_training_record(app, version_id, "forecast")

    features_df = None
    pipeline = None
    metrics = None
    try:
        for progress, stage in PROGRESS_STAGES_FORECAST:
            _update_progress(app, version_id, "forecast", progress, stage)
            if stage == "feature_engine":
                feature_engine = FeatureEngine(parsed)
                features_df = feature_engine.generate_forecast_features()
            elif stage == "model_init":
                pipeline = ForecastingPipeline(features_df)
            elif stage == "model_train":
                metrics = pipeline.train()

        app.state.forecast_pipeline = pipeline
        _finalize(app, version_id, "forecast", "completed", metrics=metrics)
        return {
            "metrics": metrics,
            "feature_count": len(features_df.columns) if features_df is not None else 0,
            "sample_count": len(features_df) if features_df is not None else 0,
        }
    except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, ImportError) as e:
        import traceback

        tb = traceback.format_exc(limit=20)
        logger.error("Forecast training failed: %s", e, exc_info=True)
        _finalize(app, version_id, "forecast", "failed", error=str(e), error_trace=tb)
        return {"error": str(e), "trace": tb}


def run_recommend_training(app, version_id: str):
    from app.core.feature_engine import RecommendationFeatureEngine
    from app.models.recommendation import HybridRecommender

    version_data = app.state.data_versions.get(version_id)
    if not version_data:
        return {"error": "version_not_found"}

    parsed = version_data["parsed_data"]
    _init_training_record(app, version_id, "recommend")

    interaction_df = None
    matrix_info = None
    product_features = None
    recommender = None
    try:
        for progress, stage in PROGRESS_STAGES_RECOMMEND:
            _update_progress(app, version_id, "recommend", progress, stage)
            if stage == "interaction_matrix":
                rec_engine = RecommendationFeatureEngine(parsed)
                interaction_df, matrix_info = rec_engine.generate_user_item_matrix()
            elif stage == "product_features":
                product_features = rec_engine.generate_product_features()
            elif stage == "model_init":
                recommender = HybridRecommender()
            elif stage == "model_train":
                recommender.fit(interaction_df, product_features)

        app.state.recommender = recommender
        _finalize(app, version_id, "recommend", "completed", matrix_info=matrix_info)
        return {
            "matrix_info": matrix_info,
            "n_products": len(product_features) if product_features is not None else 0,
        }
    except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, ImportError) as e:
        import traceback

        tb = traceback.format_exc(limit=20)
        logger.error("Recommender training failed: %s", e, exc_info=True)
        _finalize(app, version_id, "recommend", "failed", error=str(e), error_trace=tb)
        return {"error": str(e), "trace": tb}


def run_classification_training(app, version_id: str):
    from app.models.classification import CustomerClassifier

    version_data = app.state.data_versions.get(version_id)
    if not version_data:
        return {"error": "version_not_found"}

    parsed = version_data["parsed_data"]
    _init_training_record(app, version_id, "classification")

    classifier = None
    train_result = None
    try:
        for progress, stage in PROGRESS_STAGES_CLASSIFICATION:
            _update_progress(app, version_id, "classification", progress, stage)
            if stage == "model_init":
                classifier = CustomerClassifier()
            elif stage == "model_train":
                train_result = classifier.train(parsed)

        app.state.classifier = classifier
        _finalize(
            app,
            version_id,
            "classification",
            "completed",
            metrics=train_result.metrics,
            summary=train_result.dataset_info,
        )
        return {
            "metrics": train_result.metrics,
            "dataset_info": train_result.dataset_info,
        }
    except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, ImportError) as e:
        import traceback

        tb = traceback.format_exc(limit=20)
        logger.error("Classification training failed: %s", e, exc_info=True)
        _finalize(app, version_id, "classification", "failed", error=str(e), error_trace=tb)
        return {"error": str(e), "trace": tb}


def run_association_training(app, version_id: str):
    from app.models.association import AssociationRuleMiner

    version_data = app.state.data_versions.get(version_id)
    if not version_data:
        return {"error": "version_not_found"}

    parsed = version_data["parsed_data"]
    _init_training_record(app, version_id, "association")

    miner = None
    summary = None
    try:
        for progress, stage in PROGRESS_STAGES_ASSOCIATION:
            _update_progress(app, version_id, "association", progress, stage)
            if stage == "basket_build":
                miner = AssociationRuleMiner()
            elif stage == "rule_mining":
                summary = miner.fit(parsed)

        app.state.association_miner = miner
        _finalize(app, version_id, "association", "completed", summary=summary)
        return {"summary": summary}
    except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, ImportError) as e:
        import traceback

        tb = traceback.format_exc(limit=20)
        logger.error("Association training failed: %s", e, exc_info=True)
        _finalize(app, version_id, "association", "failed", error=str(e), error_trace=tb)
        return {"error": str(e), "trace": tb}


def run_clustering_training(app, version_id: str):
    from app.models.clustering import CustomerClusterer

    version_data = app.state.data_versions.get(version_id)
    if not version_data:
        return {"error": "version_not_found"}

    parsed = version_data["parsed_data"]
    _init_training_record(app, version_id, "clustering")

    clusterer = None
    summary = None
    try:
        for progress, stage in PROGRESS_STAGES_CLUSTERING:
            _update_progress(app, version_id, "clustering", progress, stage)
            if stage == "model_init":
                clusterer = CustomerClusterer()
            elif stage == "model_train":
                summary = clusterer.fit(parsed)

        app.state.clusterer = clusterer
        _finalize(app, version_id, "clustering", "completed", summary=summary)
        return {"summary": summary}
    except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, ImportError) as e:
        import traceback

        tb = traceback.format_exc(limit=20)
        logger.error("Clustering training failed: %s", e, exc_info=True)
        _finalize(app, version_id, "clustering", "failed", error=str(e), error_trace=tb)
        return {"error": str(e), "trace": tb}


def run_prophet_training(app, version_id: str):
    from app.models.timeseries import TotalProphetForecaster

    version_data = app.state.data_versions.get(version_id)
    if not version_data:
        return {"error": "version_not_found"}

    parsed = version_data["parsed_data"]
    _init_training_record(app, version_id, "prophet")

    forecaster = None
    summary = None
    try:
        for progress, stage in PROGRESS_STAGES_PROPHET:
            _update_progress(app, version_id, "prophet", progress, stage)
            if stage == "model_init":
                forecaster = TotalProphetForecaster()
            elif stage == "model_train":
                summary = forecaster.train(parsed)

        app.state.prophet_forecaster = forecaster
        _finalize(app, version_id, "prophet", "completed", summary=summary)
        return {"summary": summary}
    except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, ImportError) as e:
        import traceback

        tb = traceback.format_exc(limit=20)
        logger.error("Prophet training failed: %s", e, exc_info=True)
        _finalize(app, version_id, "prophet", "failed", error=str(e), error_trace=tb)
        return {"error": str(e), "trace": tb}
