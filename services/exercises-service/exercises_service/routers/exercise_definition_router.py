import re
from pathlib import Path

from exercises_service import schemas
from exercises_service.config import get_settings
from exercises_service.decorators import validate_exercise_definition
from exercises_service.dependencies import get_db
from exercises_service.redis_client import get_redis_client
from exercises_service.services.exercise_definition_service import ExerciseDefinitionService
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/definitions")

_ID_PATTERN = re.compile(r'^\d+$')


def _media_dir_for_exercise(exercise_list_id: int) -> Path:
    settings = get_settings()
    base = Path(settings.EXERCISES_MEDIA_DIR)
    return base / str(exercise_list_id)


_GIF_PATTERNS = {
    "gif": {
        "signatures": [b"GIF87a", b"GIF89a"],
        "content_types": {"image/gif"},
        "max_size": 25 * 1024 * 1024,
    }
}


def _validate_gif_upload(file: UploadFile, data: bytes) -> str:
    gif_config = _GIF_PATTERNS["gif"]
    
    if len(data) > gif_config["max_size"]:
        raise HTTPException(
            status_code=413, 
            detail=f"GIF file too large (max {gif_config['max_size'] // (1024*1024)}MB)"
        )
    
    is_gif = any(data.startswith(signature) for signature in gif_config["signatures"])
    if not is_gif:
        raise HTTPException(status_code=400, detail="Invalid or unsupported file format. Only GIF files are supported.")
    
    if file.content_type and file.content_type not in gif_config["content_types"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid content-type for GIF: {file.content_type}. Expected: image/gif"
        )
    
    return "gif"

@router.get("/", response_model=list[schemas.ExerciseListResponse])
async def list_exercise_definitions(
    ids: str | None = None,
    limit: int = 50,
    offset: int = 0,
    muscle_group: str | None = None,
    equipment: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    parsed_ids = None
    if ids:
        id_parts = ids.split(",")
        parsed_ids = []
        for part in id_parts:
            part = part.strip()
            if part and _ID_PATTERN.match(part):
                parsed_ids.append(int(part))
            elif part:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid ID format: '{part}'. All IDs must be valid integers."
                )
    
    muscle_groups = None
    if muscle_group:
        muscle_groups = [mg.strip() for mg in muscle_group.split(',') if mg.strip()]
    
    equipment_types = None
    if equipment:
        equipment_types = [eq.strip() for eq in equipment.split(',') if eq.strip()]
    
    service = ExerciseDefinitionService(db, redis_client)
    
    if parsed_ids is not None:
        return await service.list_definitions(parsed_ids)
    
    return await service.list_definitions(
        ids=None,
        limit=limit,
        offset=offset,
        muscle_groups=muscle_groups,
        equipment_types=equipment_types,
        search=search
    )


@router.get("/{exercise_list_id}", response_model=schemas.ExerciseListResponse)
@validate_exercise_definition()
async def get_exercise_definition(
    exercise_list_id: int, 
    db: AsyncSession = Depends(get_db), 
    redis_client = Depends(get_redis_client),
    _exercise_definition=None
):
    return _exercise_definition


@router.post("/", response_model=schemas.ExerciseListResponse, status_code=status.HTTP_201_CREATED)
async def create_exercise_definition(
    exercise: schemas.ExerciseListCreate, 
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    service = ExerciseDefinitionService(db, redis_client)
    definition = await service.create_definition(exercise)
    EXERCISE_DEFINITIONS_CREATED_TOTAL.inc()
    return definition


@router.post("/{exercise_list_id}/media/image", response_model=schemas.ExerciseListResponse)
@validate_exercise_definition()
async def upload_exercise_image(
    exercise_list_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
    _exercise_definition=None,
):
    definition = _exercise_definition

    service = ExerciseDefinitionService(db, redis_client)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    kind = _validate_gif_upload(file, data)
    ext = "gif"

    media_dir = _media_dir_for_exercise(exercise_list_id)
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / f"image.{ext}"
    target.write_bytes(data)

    update_payload = schemas.ExerciseListCreate(**definition.model_dump())
    update_payload = update_payload.model_copy(
        update={
            "image_url": f"/exercises/definitions/{exercise_list_id}/media/image",
            "gif_url": None,
        }
    )
    return await service.update_definition(exercise_list_id, update_payload)


@router.post("/{exercise_list_id}/media/gif", response_model=schemas.ExerciseListResponse)
@validate_exercise_definition()
async def upload_exercise_gif(
    exercise_list_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
    _exercise_definition=None,
):
    definition = _exercise_definition

    service = ExerciseDefinitionService(db, redis_client)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    _validate_gif_upload(file, data)

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


@router.get("/{exercise_list_id}/media/gif")
async def get_exercise_gif(exercise_list_id: int):
    media_dir = _media_dir_for_exercise(exercise_list_id)
    gif_path = media_dir / "animation.gif"
    if gif_path.exists():
        return FileResponse(gif_path, media_type="image/gif")
    raise HTTPException(status_code=404, detail="Exercise gif not found")


@router.put("/{exercise_list_id}", response_model=schemas.ExerciseListResponse)
@validate_exercise_definition()
async def update_exercise_definition(
    exercise_list_id: int,
    exercise_update: schemas.ExerciseListCreate,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
):
    service = ExerciseDefinitionService(db, redis_client)
    return await service.update_definition(exercise_list_id, exercise_update)


@router.post("/batch-upsert", response_model=list[schemas.ExerciseListResponse])
async def batch_upsert_exercise_definitions(
    exercises: list[schemas.ExerciseListCreate],
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
):
    service = ExerciseDefinitionService(db, redis_client)
    return await service.batch_upsert_definitions(exercises)


@router.delete("/{exercise_list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_definition(
    exercise_list_id: int, 
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    service = ExerciseDefinitionService(db, redis_client)
    await service.delete_definition(exercise_list_id)
