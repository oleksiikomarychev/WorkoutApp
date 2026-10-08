import logging
import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from ..config import settings


def _ensure_gemini_api_key() -> None:
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable must be set")

    os.environ["GOOGLE_API_KEY"] = google_api_key


def _ensure_fireworks_api_key() -> str:
    api_key = os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        raise ValueError("FIREWORKS_API_KEY environment variable must be set")
    return api_key


def get_chat_llm(*, temperature: float = 0.7, provider: str | None = None, model: str | None = None) -> BaseChatModel:
    chosen_provider = (provider or settings.llm_provider).lower()
    model_name: str = model or settings.llm_model

    if chosen_provider == "gemini":
        _ensure_gemini_api_key()
        logging.info("Using Gemini model %s", model_name)
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)

    if chosen_provider == "fireworks":
        api_key = _ensure_fireworks_api_key()
        base_url = os.getenv("FIREWORKS_BASE_URL") or "https://api.fireworks.ai/inference/v1"
        logging.info("Using Fireworks model %s", model_name)
        try:
            return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, temperature=temperature)
        except TypeError:
            return ChatOpenAI(model=model_name, openai_api_key=api_key, openai_api_base=base_url, temperature=temperature)

    raise ValueError(f"Unsupported LLM provider: {chosen_provider}")
