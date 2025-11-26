import io
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from huggingface_hub import InferenceClient
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dependencies import get_current_user_id, get_db
from ..metrics import AVATARS_APPLIED_TOTAL, AVATARS_GENERATED_TOTAL
from ..models import Avatar

router = APIRouter()

# Global prompt prefix to enforce consistent style
_AVATAR_PROMPT_PREFIX = (
    "Style: Apple emoji; Background: total white; Lighting: soft; Framing: centered headshot; "
    "High quality; Perspective: en face"
)


class AvatarRequest(BaseModel):
    prompt: str
    model: Optional[str] = "fofr/sdxl-emoji"


@router.post("/generate", response_class=StreamingResponse)
def generate_avatar(req: AvatarRequest, request: Request):
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise HTTPException(status_code=500, detail="HF_TOKEN is not configured")

    try:
        client = InferenceClient(provider="fal-ai", api_key=hf_token)
        uid = request.headers.get("X-User-Id")
        user_prompt = (req.prompt or "").strip()
        if _AVATAR_PROMPT_PREFIX:
            base_prompt = f"{_AVATAR_PROMPT_PREFIX}. {user_prompt}" if user_prompt else _AVATAR_PROMPT_PREFIX
        else:
            base_prompt = user_prompt
        salted_prompt = base_prompt if not uid else f"{base_prompt} (unique user token: {uid[:8]})"
        image = client.text_to_image(salted_prompt, model=req.model)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Avatar generation failed: {e}")

    buf = io.BytesIO()
    try:
        image.save(buf, format="PNG")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to encode image: {e}")
    buf.seek(0)

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
