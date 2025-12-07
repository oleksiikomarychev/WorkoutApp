import logging
import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import settings


def _ensure_google_api_key() -> None:
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable must be set")

    os.environ["GOOGLE_API_KEY"] = google_api_key


def get_chat_llm(*, temperature: float = 0.7) -> BaseChatModel:
    _ensure_google_api_key()
    model_name: str = settings.llm_model
    logging.info("Using Gemini model %s", model_name)
    return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
