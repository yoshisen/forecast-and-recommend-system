"""Association rules API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.training_events import run_association_training
from app.schemas.schemas import APIResponse


router = APIRouter(prefix="/association")


def _resolve_version_or_404(request: Request, version: Optional[str]) -> str:
    version_id = version or request.app.state.current_version
    if not version_id or version_id not in request.app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    return version_id


@router.post("/train", response_model=APIResponse)
async def train_association_model(request: Request, version: Optional[str] = Query(None)):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    result = run_association_training(app, version_id)
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"関連ルール訓練エラー: {result['error']}")

    return {
        "success": True,
        "data": result,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.get("/rules", response_model=APIResponse)
async def get_rules(
    request: Request,
    top_k: int = Query(50, ge=1, le=500),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    miner = getattr(app.state, "association_miner", None)
    if miner is None:
        raise HTTPException(status_code=400, detail="関連ルールモデルが訓練されていません")

    rules = miner.list_rules(top_k=top_k)
    return {
        "success": True,
        "data": {
            "rules": rules,
            "count": len(rules),
            "summary": getattr(miner, "summary", {}),
        },
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.get("/recommendations", response_model=APIResponse)
async def get_association_recommendations(
    request: Request,
    product_id: str = Query(...),
    top_k: int = Query(10, ge=1, le=100),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    miner = getattr(app.state, "association_miner", None)
    if miner is None:
        raise HTTPException(status_code=400, detail="関連ルールモデルが訓練されていません")

    recommendations = miner.recommend(product_id=product_id, top_k=top_k)
    return {
        "success": True,
        "data": {
            "product_id": product_id,
            "recommendations": recommendations,
            "count": len(recommendations),
        },
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }
