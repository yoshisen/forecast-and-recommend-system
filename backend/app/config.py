"""
Application configuration and settings
"""
from pydantic_settings import BaseSettings
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "LUMI Retail Analytics System"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    
    # File Upload
    UPLOAD_DIR: Path = Path("data/uploaded")
    PROCESSED_DIR: Path = Path("data/processed")
    MODELS_DIR: Path = Path("data/models")
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: set = {".xlsx", ".xls", ".csv", ".zip"}
    
    # Data Processing
    CHUNK_SIZE: int = 50000  # For large file processing
    MAX_MISSING_RATE: float = 0.60  # 60% threshold to exclude field
    WARNING_MISSING_RATE: float = 0.30  # 30% threshold to warn
    TIMEZONE: str = "Asia/Tokyo"
    
    # Model Training
    FORECAST_HORIZON: int = 14  # Default forecast days
    MIN_HISTORY_DAYS: int = 90  # Minimum 3 months
    TEST_SIZE: float = 0.2
    RANDOM_STATE: int = 42
    
    # Recommendation
    TOP_K_RECOMMEND: int = 10
    MIN_INTERACTIONS: int = 3  # Minimum purchases for collaborative filtering
    COLD_START_ITEMS: int = 20  # Popular items for cold start
    
    # Performance
    CACHE_TTL: int = 3600  # 1 hour
    MAX_WORKERS: int = 4  # Parallel processing
    
    # Security
    ENABLE_CORS: bool = True
    ALLOWED_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    DELETE_AFTER_PARSE: bool = False  # Keep uploaded files for debugging
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env file


# Global settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
os.makedirs(settings.MODELS_DIR, exist_ok=True)
