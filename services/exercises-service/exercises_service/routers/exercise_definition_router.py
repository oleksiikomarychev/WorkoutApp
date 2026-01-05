from pathlib import Path

from exercises_service import schemas
from exercises_service.config import get_settings
from exercises_service.dependencies import get_db
from exercises_service.metrics import EXERCISE_DEFINITIONS_CREATED_TOTAL
from exercises_service.services.exercise_definition_service import ExerciseDefinitionService
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/definitions")


def _media_dir_for_exercise(exercise_list_id: int) -> Path:
    settings = get_settings()
    base = Path(settings.EXERCISES_MEDIA_DIR)
    return base / str(exercise_list_id)


def _detect_image_kind(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    return None


def _validate_upload(file: UploadFile, data: bytes, allowed_kinds: set[str]) -> str:
    kind = _detect_image_kind(data)
    if kind is None or kind not in allowed_kinds:
        raise HTTPException(status_code=400, detail="Unsupported or invalid image format")

    # Content-type guard (client-provided, but still useful)
    allowed_content_types = {
        "png": {"image/png"},
        "jpeg": {"image/jpeg", "image/jpg"},
        "gif": {"image/gif"},
    }
    if file.content_type and file.content_type not in allowed_content_types.get(kind, set()):
        raise HTTPException(status_code=400, detail=f"Invalid content-type for {kind}: {file.content_type}")

    return kind


@router.get("/", response_model=list[schemas.ExerciseListResponse])
async def list_exercise_definitions(ids: str | None = None, db: AsyncSession = Depends(get_db)):
    parsed_ids = [int(id_str) for id_str in ids.split(",")] if ids else None
    service = ExerciseDefinitionService(db)
    return await service.list_definitions(parsed_ids)


@router.get("/{exercise_list_id}", response_model=schemas.ExerciseListResponse)
async def get_exercise_definition(exercise_list_id: int, db: AsyncSession = Depends(get_db)):
    service = ExerciseDefinitionService(db)
    definition = await service.get_definition(exercise_list_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    return definition


@router.post("/", response_model=schemas.ExerciseListResponse, status_code=status.HTTP_201_CREATED)
async def create_exercise_definition(exercise: schemas.ExerciseListCreate, db: AsyncSession = Depends(get_db)):
    service = ExerciseDefinitionService(db)
    definition = await service.create_definition(exercise)
    EXERCISE_DEFINITIONS_CREATED_TOTAL.inc()
    return definition


@router.post("/{exercise_list_id}/media/image", response_model=schemas.ExerciseListResponse)
async def upload_exercise_image(
    exercise_list_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    service = ExerciseDefinitionService(db)
    definition = await service.get_definition(exercise_list_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Exercise definition not found")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image file too large")

    kind = _validate_upload(file, data, {"png", "jpeg"})
    ext = "png" if kind == "png" else "jpg"

    media_dir = _media_dir_for_exercise(exercise_list_id)
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / f"image.{ext}"
    target.write_bytes(data)

    # Persist URL (served by GET endpoint)
    update_payload = schemas.ExerciseListCreate(**definition.model_dump())
    update_payload = update_payload.model_copy(
        update={
            "image_url": f"/exercises/definitions/{exercise_list_id}/media/image",
            "gif_url": None,
        }
    )
    return await service.update_definition(exercise_list_id, update_payload)


@router.post("/{exercise_list_id}/media/gif", response_model=schemas.ExerciseListResponse)
async def upload_exercise_gif(
    exercise_list_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    service = ExerciseDefinitionService(db)
    definition = await service.get_definition(exercise_list_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Exercise definition not found")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="GIF file too large")

    _validate_upload(file, data, {"gif"})

    media_dir = _media_dir_for_exercise(exercise_list_id)
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / "animation.gif"
    target.write_bytes(data)

    update_payload = schemas.ExerciseListCreate(**definition.model_dump())
    update_payload = update_payload.model_copy(
        update={
            "gif_url": f"/exercises/definitions/{exercise_list_id}/media/gif",
            "image_url": None,
        }
    )
    return await service.update_definition(exercise_list_id, update_payload)


@router.get("/{exercise_list_id}/media/image")
async def get_exercise_image(exercise_list_id: int):
    media_dir = _media_dir_for_exercise(exercise_list_id)
    png_path = media_dir / "image.png"
    jpg_path = media_dir / "image.jpg"
    if png_path.exists():
        return FileResponse(png_path, media_type="image/png")
    if jpg_path.exists():
        return FileResponse(jpg_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Exercise image not found")


@router.get("/{exercise_list_id}/media/gif")
async def get_exercise_gif(exercise_list_id: int):
    media_dir = _media_dir_for_exercise(exercise_list_id)
    gif_path = media_dir / "animation.gif"
    if gif_path.exists():
        return FileResponse(gif_path, media_type="image/gif")
    raise HTTPException(status_code=404, detail="Exercise gif not found")


@router.put("/{exercise_list_id}", response_model=schemas.ExerciseListResponse)
async def update_exercise_definition(
    exercise_list_id: int,
    exercise_update: schemas.ExerciseListCreate,
    db: AsyncSession = Depends(get_db),
):
    service = ExerciseDefinitionService(db)
    definition = await service.get_definition(exercise_list_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    return await service.update_definition(exercise_list_id, exercise_update)


@router.post("/batch-upsert", response_model=list[schemas.ExerciseListResponse])
async def batch_upsert_exercise_definitions(
    exercises: list[schemas.ExerciseListCreate],
    db: AsyncSession = Depends(get_db),
):
    service = ExerciseDefinitionService(db)
    return await service.batch_upsert_definitions(exercises)


@router.delete("/{exercise_list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_definition(exercise_list_id: int, db: AsyncSession = Depends(get_db)):
    service = ExerciseDefinitionService(db)
    await service.delete_definition(exercise_list_id)
