import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # رابط الاتصال بقاعدة بيانات PostgreSQL الموحد في الـ Docker Compose
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://admin:kave_pass@localhost:5432/kave_db"
    )

settings = Settings()