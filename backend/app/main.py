"""
Main FastAPI Application
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from app.config import settings
from app.api.v1.forecast import router as forecast_router
from app.api.v1.recommend import router as recommend_router
from app.api.v1.data import router as data_router
from app.api.v1.classification import router as classification_router
from app.api.v1.association import router as association_router
from app.api.v1.clustering import router as clustering_router
from app.api.v1.timeseries import router as timeseries_router

# ロギング設定
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS設定
if settings.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# グローバル状態（簡易版、後でRedis等に移行可能）
app.state.data_versions = {}
app.state.current_version = None
app.state.forecast_pipeline = None
app.state.recommender = None
app.state.classifier = None
app.state.association_miner = None
app.state.clusterer = None
app.state.prophet_forecaster = None
app.state.ws_clients = set()

# APIルーターを登録
app.include_router(data_router, prefix=f"{settings.API_V1_PREFIX}", tags=["data"])
app.include_router(forecast_router, prefix=f"{settings.API_V1_PREFIX}", tags=["forecast"])
app.include_router(recommend_router, prefix=f"{settings.API_V1_PREFIX}", tags=["recommend"])
app.include_router(classification_router, prefix=f"{settings.API_V1_PREFIX}", tags=["classification"])
app.include_router(association_router, prefix=f"{settings.API_V1_PREFIX}", tags=["association"])
app.include_router(clustering_router, prefix=f"{settings.API_V1_PREFIX}", tags=["clustering"])
app.include_router(timeseries_router, prefix=f"{settings.API_V1_PREFIX}", tags=["timeseries"])


@app.on_event("startup")
async def startup_event():
    """起動時の初期化"""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Upload directory: %s", settings.UPLOAD_DIR)
    logger.info("Debug mode: %s", settings.DEBUG)


@app.on_event("shutdown")
async def shutdown_event():
    """終了時のクリーンアップ"""
    logger.info("Shutting down application")


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }


@app.get("/api/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.APP_VERSION
    }


@app.websocket("/api/v1/ws/training")
async def training_ws(ws: WebSocket):
    """Training progress websocket endpoint."""
    await ws.accept()
    app.state.ws_clients.add(ws)
    try:
        while True:
            # Keep-alive: we ignore incoming messages, but receive to detect disconnect cleanly
            await ws.receive_text()
    except WebSocketDisconnect:
        app.state.ws_clients.discard(ws)
    except (RuntimeError, ValueError, ConnectionError):
        app.state.ws_clients.discard(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
