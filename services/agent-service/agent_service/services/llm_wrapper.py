from typing import Any, Dict

from ..config import settings
from .plan_generation import _genai_generate_json


async def generate_structured_output(
    *,
    prompt: str,
    response_schema: Dict[str, Any],
    temperature: float = 0.3,
    max_output_tokens: int = 2048,
) -> Dict[str, Any]:
    """Generate structured JSON output using the configured LLM provider.

    For now this delegates to Gemini via `_genai_generate_json`. Later we can
    swap the underlying provider (e.g. Hugging Face Inference) based on
    `LLM_PROVIDER` / `STAGED_LLM_PROVIDER` without touching callers.
    """

    provider = settings.staged_llm_provider

    if provider == "gemini":
        return await _genai_generate_json(
            prompt=prompt,
            response_schema=response_schema,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    raise RuntimeError(f"Unsupported structured LLM provider: {provider}")
