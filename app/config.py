from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str
    openai_base_url: Optional[str] = None   # для прокси / совместимых API

    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    elasticsearch_index_pattern: str = "windows-*"

    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"
    LANGFUSE_DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()