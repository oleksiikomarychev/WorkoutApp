import io
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dependencies import get_current_user_id, get_db
from ..metrics import AVATARS_APPLIED_TOTAL, AVATARS_GENERATED_TOTAL
from ..models import Avatar
from ..prompts.avatars import AVATAR_PROMPT_PREFIX

router = APIRouter()


class AvatarRequest(BaseModel):
    prompt: str
    model: str | None = "fofr/sdxl-emoji"


@router.post("/generate", response_class=StreamingResponse)
def generate_avatar(req: AvatarRequest, request: Request):
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise HTTPException(status_code=500, detail="HF_TOKEN is not configured")

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
        resp = httpx.post(api_url, headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        image_bytes = resp.content
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Avatar generation failed: {e}")

    buf = io.BytesIO(image_bytes)

    AVATARS_GENERATED_TOTAL.inc()
    return StreamingResponse(buf, media_type="image/png")


@router.post("/apply")
async def apply_avatar(request: Request, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    raw: bytes = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty body")

    if len(raw) < 16:
        raise HTTPException(status_code=400, detail="Invalid image data")

    try:
        existing = db.get(Avatar, user_id)
        if existing:
            existing.image = raw
        else:
            existing = Avatar(user_id=user_id, image=raw)
            db.add(existing)
        db.commit()
        AVATARS_APPLIED_TOTAL.inc()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save avatar: {e}")
    return {"uid": user_id, "ok": True}


@router.get("/{uid}.png")
def get_avatar(uid: str, db: Session = Depends(get_db)):
    row = db.get(Avatar, uid)
    if not row or not row.image:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return StreamingResponse(io.BytesIO(row.image), media_type=row.content_type or "image/png")
