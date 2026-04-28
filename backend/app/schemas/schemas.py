"""
Pydantic Schemas - データ検証とシリアライズ
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class UploadResponse(BaseModel):
    """アップロードレスポンス"""
    success: bool
    version: str
    parse_report: Dict[str, Any]
    quality_report: Dict[str, Any]
    validation_result: Dict[str, Any]
    warnings: List[Dict[str, str]]
    metadata: Dict[str, Any]


class DataSummary(BaseModel):
    """データサマリー"""
    version: str
    uploaded_at: str
    filename: str
    overall_summary: Dict[str, Any]
    sheet_summaries: Dict[str, Dict[str, Any]]
    training: Optional[Dict[str, Any]] = None
    task_readiness: Optional[Dict[str, Any]] = None


class ForecastRequest(BaseModel):
    """予測リクエスト"""
    product_id: str
    store_id: str
    horizon: int = Field(default=14, ge=1, le=90)
    use_baseline: bool = False
    algorithm: str = "lightgbm"


class BatchForecastRequest(BaseModel):
    """バッチ予測リクエスト"""
    pairs: List[Dict[str, str]]
    horizon: int = Field(default=14, ge=1, le=90)


class ForecastResponse(BaseModel):
    """予測レスポンス"""
    product_id: str
    store_id: str
    requested_algorithm: str
    algorithm: str
    method: str
    horizon: int
    predictions: List[float]
    dates: List[str]
    total_forecast: float
    avg_daily_forecast: float


class TotalForecastResponse(BaseModel):
    """Home画面向け総額予測レスポンス"""
    version: str
    horizon: int
    method: str
    model_type: str
    metric: str
    dates: List[str]
    totals: List[float]
    cumulative_total: float
    avg_daily_total: float
    model_ready: bool
    fallback_used: bool
    note: Optional[str] = None


class RecommendRequest(BaseModel):
    """推薦リクエスト"""
    customer_id: str
    top_k: int = Field(default=10, ge=1, le=50)


class RecommendResponse(BaseModel):
    """推薦レスポンス"""
    customer_id: str
    recommendations: List[Dict[str, Any]]
    method: str
    timestamp: str


class PopularRecommendRequest(BaseModel):
    """人気商品推薦リクエスト"""
    top_k: int = Field(default=10, ge=1, le=50)
    store_id: Optional[str] = None


class APIResponse(BaseModel):
    """統一APIレスポンス"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any]
