"""
Recommendation API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
from datetime import datetime
import logging

from app.schemas.schemas import APIResponse
from app.core.training_events import run_recommend_training

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommend")


@router.get("", response_model=APIResponse)
async def get_recommendations(
    request: Request,
    customer_id: str = Query(..., description="顧客ID"),
    top_k: int = Query(10, ge=1, le=50, description="推薦数"),
    version: Optional[str] = Query(None, description="データバージョン")
):
    """
    顧客向け個別推薦
    
    Args:
        customer_id: 顧客ID
        top_k: 推薦商品数
        version: データバージョン
    
    Returns:
        推薦結果
    """
    app = request.app
    version_id = version or app.state.current_version
    
    if not version_id or version_id not in app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    
    # レコメンダーを取得
    if not hasattr(app.state, 'recommender') or app.state.recommender is None:
        raise HTTPException(status_code=400, detail="推薦モデルが訓練されていません")
    
    recommender = app.state.recommender
    
    try:
        recommendations = recommender.recommend(customer_id, top_k)
        
        return {
            'success': True,
            'data': {
                'customer_id': customer_id,
                'recommendations': recommendations,
                'count': len(recommendations),
                'method': 'hybrid'
            },
            'error': None,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'version': version_id
            }
        }
    
    except Exception as e:
        logger.error("Recommendation error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"推薦エラー: {str(e)}")


@router.get("/popular", response_model=APIResponse)
async def get_popular_recommendations(
    request: Request,
    top_k: int = Query(10, ge=1, le=50, description="推薦数"),
    store_id: Optional[str] = Query(None, description="店舗ID"),
    version: Optional[str] = Query(None, description="データバージョン")
):
    """
    人気商品推薦（コールドスタート用）
    
    Args:
        top_k: 推薦商品数
        store_id: 店舗ID（オプション）
        version: データバージョン
    
    Returns:
        人気商品リスト
    """
    app = request.app
    version_id = version or app.state.current_version
    
    if not version_id or version_id not in app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    
    if not hasattr(app.state, 'recommender') or app.state.recommender is None:
        raise HTTPException(status_code=400, detail="推薦モデルが訓練されていません")
    
    recommender = app.state.recommender
    
    try:
        recommendations = recommender.recommend_popular(top_k, store_id)
        
        return {
            'success': True,
            'data': {
                'recommendations': recommendations,
                'count': len(recommendations),
                'method': 'popular',
                'store_id': store_id
            },
            'error': None,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'version': version_id
            }
        }
    
    except Exception as e:
        logger.error("Popular recommendation error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"人気商品推薦エラー: {str(e)}")


@router.post("/train")
async def train_recommender(request: Request, version: Optional[str] = Query(None)):
    """
    推薦モデルを訓練
    
    Args:
        version: データバージョン
    
    Returns:
        訓練結果
    """
    app = request.app
    # Use centralized training with progress broadcasting
    
    version_id = version or app.state.current_version
    
    if not version_id or version_id not in app.state.data_versions:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    
    try:
        logger.info("Training recommender for version %s", version_id)
        result = run_recommend_training(app, version_id)
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
        logger.error("Recommender training error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"訓練エラー: {str(e)}")
