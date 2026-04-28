"""
Forecast API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
from datetime import datetime
import logging

from app.schemas.schemas import BatchForecastRequest, APIResponse
from app.core.training_events import run_forecast_training

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecast")


@router.get("", response_model=APIResponse)
async def get_forecast(
    request: Request,
    product_id: str = Query(..., description="商品ID"),
    store_id: str = Query(..., description="店舗ID"),
    horizon: int = Query(14, ge=1, le=90, description="予測期間（日数)"),
    use_baseline: bool = Query(False, description="ベースラインモデルを使用"),
    algorithm: str = Query("lightgbm", description="lightgbm | sarima | xgboost | baseline"),
    version: Optional[str] = Query(None, description="データバージョン")
):
    """
    単一商品の販売予測を取得
    
    Args:
        product_id: 商品ID
        store_id: 店舗ID
        horizon: 予測期間（日数）
        use_baseline: ベースラインモデルを使用するか
        algorithm: 予測アルゴリズム (lightgbm | sarima | xgboost | baseline)
        version: データバージョン（省略時は最新）
    
    Returns:
        予測結果
    """
    app = request.app
    version_id = version or app.state.current_version
    
    if not version_id or version_id not in app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    
    # パイプラインを取得
    if not hasattr(app.state, 'forecast_pipeline') or app.state.forecast_pipeline is None:
        raise HTTPException(status_code=400, detail="予測モデルが訓練されていません")
    
    pipeline = app.state.forecast_pipeline
    
    try:
        result = pipeline.forecast(product_id, store_id, horizon, use_baseline, algorithm)
        
        return {
            'success': True,
            'data': result,
            'error': None,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'version': version_id
            }
        }
    
    except Exception as e:
        logger.error("Forecast error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"予測エラー: {str(e)}") from e


@router.post("/batch", response_model=APIResponse)
async def batch_forecast(
    request: Request,
    body: BatchForecastRequest,
    version: Optional[str] = Query(None)
):
    """
    バッチ予測
    
    Args:
        request: バッチ予測リクエスト
        version: データバージョン
    
    Returns:
        予測結果リスト
    """
    app = request.app
    version_id = version or app.state.current_version
    
    if not version_id or version_id not in app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    
    if not hasattr(app.state, 'forecast_pipeline') or app.state.forecast_pipeline is None:
        raise HTTPException(status_code=400, detail="予測モデルが訓練されていません")
    
    pipeline = app.state.forecast_pipeline
    
    try:
        # ペアのリストを作成
        pairs = [(p['product_id'], p['store_id']) for p in body.pairs]
        results = pipeline.batch_forecast(pairs, body.horizon)
        
        return {
            'success': True,
            'data': {
                'forecasts': results,
                'count': len(results)
            },
            'error': None,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'version': version_id,
                'horizon': body.horizon
            }
        }
    
    except Exception as e:
        logger.error("Batch forecast error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"バッチ予測エラー: {str(e)}") from e


@router.post("/train", response_model=APIResponse)
async def train_forecast_model(request: Request, version: Optional[str] = Query(None)):
    """予測モデルを訓練し進捗を初期化/更新する"""
    app = request.app
    version_id = version or app.state.current_version

    if not version_id or version_id not in app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")

    try:
        logger.info("Training forecast model for version %s", version_id)
        result = run_forecast_training(app, version_id)
        if 'error' in result:
            raise HTTPException(status_code=500, detail=f"訓練エラー: {result['error']}")
        return {
            'success': True,
            'data': result,
            'error': None,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'version': version_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Training error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"訓練エラー: {str(e)}") from e
