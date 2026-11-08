"""Avatar generation and storage router for agent-service."""

from __future__ import annotations

import io
import os

from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..dependencies import get_current_user_id, get_db
from ..metrics import AVATARS_APPLIED_TOTAL, AVATARS_GENERATED_TOTAL
from ..models import Avatar
from ..prompts.avatars import AVATAR_PROMPT_PREFIX

logger = structlog.get_logger(__name__)
router = APIRouter()


class AvatarRequest(BaseModel):
    prompt: str = Field(..., description="Prompt describing the avatar image")
    model: str | None = Field(default="fofr/sdxl-emoji", description="HuggingFace model ID")


@router.post("/generate", response_class=StreamingResponse)
async def generate_avatar(req: AvatarRequest, request: Request) -> StreamingResponse:
    hf_token = settings.HF_TOKEN or os.environ.get("HF_TOKEN")
    if not hf_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HF_TOKEN is not configured",
        )

    try:
        uid = request.headers.get("X-User-Id")
        user_prompt = (req.prompt or "").strip()
        if AVATAR_PROMPT_PREFIX:
            base_prompt = f"{AVATAR_PROMPT_PREFIX}. {user_prompt}" if user_prompt else AVATAR_PROMPT_PREFIX
        else:
            base_prompt = user_prompt
        salted_prompt = base_prompt if not uid else f"{base_prompt} (unique user token: {uid[:8]})"

        model_id = req.model or "fofr/sdxl-emoji"
        api_url = f"https://router.huggingface.co/models/{model_id}"
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Accept": "image/png",
        }
        payload = {"inputs": salted_prompt}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(api_url, headers=headers, json=payload)
            resp.raise_for_status()
            image_bytes = resp.content
    except httpx.HTTPStatusError as exc:
        logger.error("hf_avatar_generation_http_error", status_code=exc.response.status_code, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Avatar generation upstream error: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("avatar_generation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Avatar generation failed: {exc}",
        ) from exc

    buf = io.BytesIO(image_bytes)
    AVATARS_GENERATED_TOTAL.inc()
    return StreamingResponse(buf, media_type="image/png")


@router.post("/apply")
async def apply_avatar(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    raw: bytes = await request.body()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty body")

    if len(raw) < 16:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image data")

    try:
        existing = db.get(Avatar, user_id)
        if existing:
            existing.image = raw
            existing.content_type = request.headers.get("content-type") or "image/png"
        else:
            existing = Avatar(
                user_id=user_id,
                image=raw,
                content_type=request.headers.get("content-type") or "image/png",
            )
            db.add(existing)
        db.commit()
        AVATARS_APPLIED_TOTAL.inc()
    except Exception as exc:
        db.rollback()
        logger.error("failed_to_save_avatar", user_id=user_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save avatar: {exc}",
        ) from exc
    return {"uid": user_id, "ok": True}


@router.get("/{uid}.png")
def get_avatar(uid: str, db: Session = Depends(get_db)) -> StreamingResponse:
    row = db.get(Avatar, uid)
    if not row or not row.image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    media_type = getattr(row, "content_type", None) or "image/png"
    return StreamingResponse(io.BytesIO(row.image), media_type=media_type)
