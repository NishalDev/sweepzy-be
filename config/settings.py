# config/settings.py

from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field, validator, SecretStr
import os
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Sweepzy"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    
    # URLs
    BACKEND_URL: str
    CLIENT_URL: str
    NGROK_URL: Optional[str] = None
    UPLOAD_URL: str
    
    # File uploads
    UPLOAD_ACCESS_TOKEN: Optional[str] = None
    UPLOAD_DIR: Optional[str] = None  # Added missing field
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, ge=1024)
    ALLOWED_FILE_TYPES: str = "jpg,jpeg,png,gif,pdf"
    
    # CORS
    CORS_ORIGINS: str = ""
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if not self.CORS_ORIGINS:
            return ["*"] if self.DEBUG else []
        return [s.strip() for s in self.CORS_ORIGINS.split(",") if s.strip()]
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types from comma-separated string"""
        return [ext.strip().lower() for ext in self.ALLOWED_FILE_TYPES.split(",")]
    
    # Database
    DATABASE_URL: str
    DB_NAME: Optional[str] = None  # Added missing field
    DB_USER: Optional[str] = None  # Added missing field
    DB_PASSWORD: Optional[str] = None  # Added missing field
    DB_HOST: Optional[str] = None  # Added missing field
    DB_PORT: Optional[str] = None  # Added missing field
    DB_POOL_SIZE: int = Field(default=20, ge=5, le=100)
    DB_MAX_OVERFLOW: int = Field(default=30, ge=5, le=100)
    DB_POOL_RECYCLE: int = Field(default=3600, ge=300)
    
    # Redis
    REDIS_URL: str
    REDIS_HOST: Optional[str] = None  # Added missing field
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=10, le=200)
    
    # Security
    SECRET_KEY: str = Field(min_length=8)  # Made more flexible for development
    ALGORITHM: str = "HS256"
    JWT_SECRET: str = Field(min_length=8)  # Made more flexible for development
    
    # Token settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, ge=15, le=1440)  # 1 hour default, max 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, ge=1, le=90)  # 30 days default
    
    # Password policy
    MIN_PASSWORD_LENGTH: int = Field(default=8, ge=6, le=128)
    REQUIRE_PASSWORD_COMPLEXITY: bool = True
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT: str = "5/minute"
    API_RATE_LIMIT: str = "100/minute"
    
    # Email
    EMAIL_FROM: str
    EMAIL_NAME: str = "Sweepzy"
    EMAIL_HOST: str
    EMAIL_PORT: int = Field(ge=1, le=65535)
    EMAIL_USER: str
    EMAIL_PASSWORD: str  # Made more flexible
    EMAIL_USE_TLS: bool = True
    EMAIL_USE_SSL: bool = False
    EMAIL_TIMEOUT: int = Field(default=30, ge=5, le=300)
    
    # OTP
    OTP_EXPIRE_MINUTES: int = Field(default=10, ge=5, le=60)
    OTP_LENGTH: int = Field(default=6, ge=4, le=8)
    
    # Caching
    CACHE_DEFAULT_TTL: int = Field(default=300, ge=60)  # 5 minutes default
    CACHE_USER_TTL: int = Field(default=900, ge=60)     # 15 minutes default
    CACHE_STATIC_TTL: int = Field(default=3600, ge=60)  # 1 hour default
    
    # ML Model settings
    MODEL_PATH: Optional[str] = None
    ML_MODEL_CACHE_SIZE: int = Field(default=1, ge=1, le=5)
    ML_CONFIDENCE_THRESHOLD: float = Field(default=0.25, ge=0.1, le=0.9)
    
    # Monitoring
    ENABLE_METRICS: bool = True
    ENABLE_HEALTH_CHECKS: bool = True
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    STRUCTURED_LOGGING: bool = True
    
    # Performance
    ENABLE_GZIP: bool = True
    ENABLE_CACHE_HEADERS: bool = True
    MAX_REQUEST_SIZE: int = Field(default=16 * 1024 * 1024, ge=1024)  # 16MB
    
    # Server
    PORT: Optional[int] = Field(default=8000, ge=1, le=65535)  # Added missing field
    
    # Application modes
    MAINTENANCE_MODE: bool = Field(default=False)  # Added missing field
    BETA_ACCESS_MODE: bool = Field(default=False)  # Added missing field
    
    @validator('SECRET_KEY', 'JWT_SECRET')
    def validate_secrets(cls, v):
        """Ensure secrets are strong enough"""
        # More flexible validation for development
        if len(v) < 8:
            raise ValueError('Secret keys must be at least 8 characters long')
        # Warn if too short for production
        if len(v) < 32:
            import warnings
            warnings.warn(f"Secret key is only {len(v)} characters. Consider using at least 32 characters for production.", UserWarning)
        return v
    
    @validator('EMAIL_HOST')
    def validate_email_host(cls, v):
        """Validate email host format"""
        if not v or len(v) < 3:
            raise ValueError('Invalid email host')
        return v
    
    @validator('DATABASE_URL')
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if not v.startswith(('postgresql://', 'postgresql+psycopg2://', 'sqlite:///')):
            raise ValueError('Unsupported database URL format')
        return v
    
    @validator('REDIS_URL')
    def validate_redis_url(cls, v):
        """Validate Redis URL format"""
        if not v.startswith(('redis://', 'rediss://')):
            raise ValueError('Invalid Redis URL format')
        return v
    
    @validator('CORS_ORIGINS')
    def validate_cors_origins(cls, v):
        """Validate CORS origins in production"""
        # In production, don't allow wildcard CORS
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production' and ('*' in v or not v):
            raise ValueError('Wildcard CORS origins not allowed in production')
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Allow extra fields for backward compatibility
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
