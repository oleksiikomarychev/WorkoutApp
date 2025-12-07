import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import settings
from .langchain_runtime import get_chat_llm


def _validate_against_schema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    if not isinstance(schema, dict):
        return

    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(payload, dict):
        raise ValueError("Structured LLM output is not an object as required by schema['type']")

    required = schema.get("required")
    if isinstance(required, list) and isinstance(payload, dict):
        missing = [key for key in required if key not in payload]
        if missing:
            missing_sorted = sorted(set(str(k) for k in missing))
            logging.error(
                "Structured LLM output missing required keys",
                extra={"missing_keys": missing_sorted},
            )
            raise ValueError("Structured LLM output missing required keys: " + ", ".join(missing_sorted))


async def generate_structured_output(
    *,
    prompt: str,
    response_schema: dict[str, Any],
    temperature: float = 0.3,
    max_output_tokens: int = 2048,
) -> dict[str, Any]:
    provider = settings.staged_llm_provider
    if provider != "gemini":
        raise RuntimeError(f"Unsupported structured LLM provider: {provider}")

    llm = get_chat_llm(temperature=temperature)

    try:
        schema_text = json.dumps(response_schema, ensure_ascii=False, indent=2)
    except TypeError:
        schema_text = str(response_schema)

    system_text = (
        "You are a JSON-only API. "
        "Respond with a single JSON object that strictly follows the given JSON schema.\n\n"
        "JSON schema (draft-style description):\n"
        f"{schema_text}\n\n"
        "Do not include any explanations, comments, or markdown. "
        "Output ONLY raw JSON for the object."
    )

    messages = [
        SystemMessage(content=system_text),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages, max_output_tokens=max_output_tokens)
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = text.strip()

    if not text:
        logging.error(
            "Empty structured LLM response",
            extra={"prompt_preview": prompt[:200]},
        )
        raise ValueError("Empty structured LLM response")

    candidate = text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.error(
            "Failed to parse structured LLM output as JSON",
            extra={"preview": candidate[:500]},
            exc_info=exc,
        )
        raise

    if not isinstance(parsed, dict):
        raise ValueError("Structured LLM output is not a JSON object")

    _validate_against_schema(parsed, response_schema)

    return parsed
