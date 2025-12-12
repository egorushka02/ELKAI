from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.config import settings


def get_langfuse_handler():
    # Устанавливаем переменные окружения перед созданием обработчика
    import os
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
    os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
    if settings.LANGFUSE_HOST:
        os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST
    
    # Создаем обработчик (он автоматически использует переменные окружения)
    return CallbackHandler()