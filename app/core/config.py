from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
import json

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI K8s Worker Prototype"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Should be from environment
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                # Parse JSON array string
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    # Fallback to treating as comma-separated
                    return [i.strip() for i in v.split(",")]
            else:
                # Comma-separated string
                return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_connection(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        postgres_server = values.data.get("POSTGRES_SERVER")
        postgres_user = values.data.get("POSTGRES_USER")
        postgres_password = values.data.get("POSTGRES_PASSWORD")
        postgres_db = values.data.get("POSTGRES_DB")
        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}/{postgres_db}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    @field_validator("REDIS_URL", mode="before")
    def assemble_redis_connection(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        redis_host = values.data.get("REDIS_HOST")
        redis_port = values.data.get("REDIS_PORT")
        redis_db = values.data.get("REDIS_DB")
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @field_validator("CELERY_BROKER_URL", mode="before")
    def set_celery_broker(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return values.data.get("REDIS_URL", "")

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    def set_celery_backend(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return values.data.get("REDIS_URL", "")

    # Logging Configuration
    LOG_DIR: str = "./logs"
    LOG_LEVEL: str = "INFO"
    LOG_ROTATION_SIZE: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_SERVICE_HOST: str = "localhost"
    LOG_SERVICE_PORT: int = 8765
    LOG_BUFFER_SIZE: int = 1000

    @field_validator("LOG_ROTATION_SIZE", "LOG_BACKUP_COUNT", "LOG_SERVICE_PORT", "LOG_BUFFER_SIZE", mode="before")
    def validate_integers(cls, v):
        if isinstance(v, str):
            # Handle comments in env values (e.g., "10485760  # 10MB")
            value = v.split('#')[0].strip()
            return int(value)
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"

settings = Settings() 