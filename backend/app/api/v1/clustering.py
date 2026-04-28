"""Clustering API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.training_events import run_clustering_training
from app.schemas.schemas import APIResponse


router = APIRouter(prefix="/clustering")


def _resolve_version_or_404(request: Request, version: Optional[str]) -> str:
    version_id = version or request.app.state.current_version
    if not version_id or version_id not in request.app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    return version_id


@router.post("/train", response_model=APIResponse)
async def train_clustering_model(
    request: Request,
    n_clusters: int = Query(4, ge=2, le=12),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    # Train via orchestrator first
    result = run_clustering_training(app, version_id)
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"クラスタリング訓練エラー: {result['error']}")

    # Optional retrain with a chosen cluster count
    clusterer = getattr(app.state, "clusterer", None)
    if clusterer is not None:
        parsed = app.state.data_versions[version_id]["parsed_data"]
        summary = clusterer.fit(parsed, n_clusters=n_clusters)
        result["summary"] = summary

    return {
        "success": True,
        "data": result,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.get("/segments", response_model=APIResponse)
async def get_segments(request: Request, version: Optional[str] = Query(None)):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    clusterer = getattr(app.state, "clusterer", None)
    if clusterer is None:
        raise HTTPException(status_code=400, detail="クラスタリングモデルが訓練されていません")

    segments = clusterer.get_segments()
    return {
        "success": True,
        "data": {
            "segments": segments,
            "count": len(segments),
            "summary": getattr(clusterer, "summary", {}),
        },
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.get("/points", response_model=APIResponse)
async def get_cluster_points(
    request: Request,
    limit: int = Query(1500, ge=100, le=10000),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    clusterer = getattr(app.state, "clusterer", None)
    if clusterer is None:
        raise HTTPException(status_code=400, detail="クラスタリングモデルが訓練されていません")

    points = clusterer.get_points(limit=limit)
    return {
        "success": True,
        "data": {
            "points": points,
            "count": len(points),
        },
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.get("/customer/{customer_id}", response_model=APIResponse)
async def get_customer_cluster(
    request: Request,
    customer_id: str,
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    clusterer = getattr(app.state, "clusterer", None)
    if clusterer is None:
        raise HTTPException(status_code=400, detail="クラスタリングモデルが訓練されていません")

    try:
        result = clusterer.get_customer_cluster(customer_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "success": True,
        "data": result,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }
