"""Classification API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.training_events import run_classification_training
from app.schemas.schemas import APIResponse


router = APIRouter(prefix="/classification")


def _resolve_version_or_404(request: Request, version: Optional[str]) -> str:
    version_id = version or request.app.state.current_version
    if not version_id or version_id not in request.app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    return version_id


@router.post("/train", response_model=APIResponse)
async def train_classification_model(request: Request, version: Optional[str] = Query(None)):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    result = run_classification_training(app, version_id)
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"分類訓練エラー: {result['error']}")

    return {
        "success": True,
        "data": result,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.get("/predict", response_model=APIResponse)
async def predict_customer_class(
    request: Request,
    customer_id: str = Query(..., description="顧客ID"),
    threshold: Optional[float] = Query(None, gt=0, lt=1),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    classifier = getattr(app.state, "classifier", None)
    if classifier is None:
        raise HTTPException(status_code=400, detail="分類モデルが訓練されていません")

    try:
        prediction = classifier.predict_customer(customer_id=customer_id, threshold=threshold)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "success": True,
        "data": prediction,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.post("/predict/features", response_model=APIResponse)
async def predict_by_features(
    request: Request,
    body: Dict[str, Any],
    threshold: Optional[float] = Query(None, gt=0, lt=1),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    classifier = getattr(app.state, "classifier", None)
    if classifier is None:
        raise HTTPException(status_code=400, detail="分類モデルが訓練されていません")

    try:
        prediction = classifier.predict_with_features(body, threshold=threshold)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "success": True,
        "data": prediction,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.get("/threshold-scan", response_model=APIResponse)
async def threshold_scan(
    request: Request,
    step: float = Query(0.05, gt=0.0, le=0.2),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    classifier = getattr(app.state, "classifier", None)
    if classifier is None:
        raise HTTPException(status_code=400, detail="分類モデルが訓練されていません")

    try:
        scan = classifier.scan_thresholds(step=step)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "success": True,
        "data": scan,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.post("/tune-threshold", response_model=APIResponse)
async def tune_threshold(
    request: Request,
    threshold: float = Query(..., gt=0.0, lt=1.0),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    classifier = getattr(app.state, "classifier", None)
    if classifier is None:
        raise HTTPException(status_code=400, detail="分類モデルが訓練されていません")

    try:
        classifier.set_threshold(threshold)
        scan = classifier.scan_thresholds(step=0.05)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "success": True,
        "data": {
            "threshold": float(threshold),
            "best_by_f1": scan.get("best_by_f1"),
        },
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }
