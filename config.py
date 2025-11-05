from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List

class Settings(BaseSettings):
    GOOGLE_API_KEY : str
    GROQ_API_KEY : str
    COHERE_API_KEY : str
    SCRAPEGRAPH_API_KEY : str
    TAVILY_API_KEY : str

    LANGSMITH_TRACING: bool
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str
    
    FAQ_DATA_PATH: str = "src/data/store_qa.csv"
    DATABASE_URL: str = "sqlite:///./customer_service.db"

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_TASK_TIME_LIMIT: int = 600
    CELERY_TASK_ACKS_LATE: bool = False
    CELERY_WORKER_CONCURRENCY: int = 2
    CELERY_TASK_MAX_RETRIES: int = 3
    CELERY_TASK_RETRY_DELAY: int = 5

    REDIS_PASSWORD: str
    REDIS_APPENDONLY: str
    REDIS_MAXMEMORY: str
    REDIS_MAXMEMORY_POLICY: str
    REDIS_PROTECTED_MODE: str

    model_config = ConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore"  # Ignore extra fields in .env that aren't in Settings
    )

def get_settings() -> Settings:
    return Settings()