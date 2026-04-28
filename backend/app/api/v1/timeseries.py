"""Time series API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.training_events import run_prophet_training
from app.schemas.schemas import APIResponse


router = APIRouter(prefix="/timeseries")


def _resolve_version_or_404(request: Request, version: Optional[str]) -> str:
    version_id = version or request.app.state.current_version
    if not version_id or version_id not in request.app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    return version_id


@router.post("/train", response_model=APIResponse)
async def train_timeseries_model(request: Request, version: Optional[str] = Query(None)):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    result = run_prophet_training(app, version_id)
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"時系列訓練エラー: {result['error']}")

    return {
        "success": True,
        "data": result,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": version_id,
        },
    }


@router.get("/forecast", response_model=APIResponse)
async def get_timeseries_forecast(
    request: Request,
    horizon: int = Query(14, ge=1, le=90),
    version: Optional[str] = Query(None),
):
    app = request.app
    version_id = _resolve_version_or_404(request, version)

    forecaster = getattr(app.state, "prophet_forecaster", None)
    if forecaster is None:
        raise HTTPException(status_code=400, detail="Prophetモデルが訓練されていません")

    try:
        result = forecaster.forecast(horizon=horizon)
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
