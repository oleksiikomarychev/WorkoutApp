from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..metrics import (
    CRM_LINKS_CREATED_TOTAL,
    CRM_NOTES_CREATED_TOTAL,
    CRM_TAG_ASSIGNMENTS_TOTAL,
    CRM_TAGS_CREATED_TOTAL,
)
from ..schemas.relationships import (
    CoachAthleteLinkCreate,
    CoachAthleteLinkResponse,
    CoachAthleteLinkStatusUpdate,
    CoachAthleteNoteCreate,
    CoachAthleteNoteResponse,
    CoachAthleteNoteUpdate,
    CoachAthleteStatus,
    CoachAthleteTagAssignRequest,
    CoachAthleteTagCreate,
    CoachAthleteTagResponse,
    CoachAthleteTagUpdate,
)
from ..services.relationships_service import (
    assign_tag_to_link,
    create_link,
    create_note_for_link,
    create_tag,
    list_athletes_for_coach,
    list_coaches_for_athlete,
    list_notes_for_link,
    list_tags,
    remove_tag_from_link,
    update_link_status,
    update_note,
    update_tag,
)

router = APIRouter(prefix="/crm/relationships", tags=["crm-relationships"])


@router.post("/", response_model=CoachAthleteLinkResponse)
async def create_coach_athlete_link(
    payload: CoachAthleteLinkCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthleteLinkResponse:
    # Текущий пользователь считается тренером
    link = await create_link(db, coach_id=user_id, payload=payload)
    CRM_LINKS_CREATED_TOTAL.inc()
    return link


@router.get("/my/athletes", response_model=List[CoachAthleteLinkResponse])
async def get_my_athletes(
    status: Optional[CoachAthleteStatus] = Query(None),
    tags: Optional[List[int]] = Query(None, description="Список ID тегов для фильтрации"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[CoachAthleteLinkResponse]:
    return await list_athletes_for_coach(
        db,
        coach_id=user_id,
        status_filter=status,
        tag_ids=tags,
        limit=limit,
        offset=offset,
    )


@router.get("/my/coaches", response_model=List[CoachAthleteLinkResponse])
async def get_my_coaches(
    status: Optional[CoachAthleteStatus] = Query(None),
    tags: Optional[List[int]] = Query(None, description="Список ID тегов для фильтрации"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[CoachAthleteLinkResponse]:
    return await list_coaches_for_athlete(
        db,
        athlete_id=user_id,
        status_filter=status,
        tag_ids=tags,
        limit=limit,
        offset=offset,
    )


@router.patch("/{link_id}/status", response_model=CoachAthleteLinkResponse)
async def patch_link_status(
    link_id: int,
    payload: CoachAthleteLinkStatusUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthleteLinkResponse:
    return await update_link_status(
        db,
        link_id=link_id,
        acting_user_id=user_id,
        payload=payload,
    )


@router.post("/{link_id}/notes", response_model=CoachAthleteNoteResponse)
async def create_note(
    link_id: int,
    payload: CoachAthleteNoteCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthleteNoteResponse:
    note = await create_note_for_link(
        db=db,
        link_id=link_id,
        acting_user_id=user_id,
        payload=payload,
    )
    CRM_NOTES_CREATED_TOTAL.inc()
    return note


@router.get("/{link_id}/notes", response_model=List[CoachAthleteNoteResponse])
async def list_notes(
    link_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[CoachAthleteNoteResponse]:
    return await list_notes_for_link(
        db=db,
        link_id=link_id,
        acting_user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.patch("/notes/{note_id}", response_model=CoachAthleteNoteResponse)
async def patch_note(
    note_id: int,
    payload: CoachAthleteNoteUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthleteNoteResponse:
    return await update_note(
        db=db,
        note_id=note_id,
        acting_user_id=user_id,
        payload=payload,
    )


@router.post("/tags", response_model=CoachAthleteTagResponse)
async def create_coach_tag(
    payload: CoachAthleteTagCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthleteTagResponse:
    tag = await create_tag(db=db, acting_user_id=user_id, payload=payload)
    CRM_TAGS_CREATED_TOTAL.inc()
    return tag


@router.get("/tags", response_model=List[CoachAthleteTagResponse])
async def list_coach_tags(
    include_inactive: bool = Query(False),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[CoachAthleteTagResponse]:
    return await list_tags(db=db, acting_user_id=user_id, include_inactive=include_inactive)


@router.patch("/tags/{tag_id}", response_model=CoachAthleteTagResponse)
async def patch_coach_tag(
    tag_id: int,
    payload: CoachAthleteTagUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthleteTagResponse:
    return await update_tag(db=db, tag_id=tag_id, acting_user_id=user_id, payload=payload)


@router.post("/{link_id}/tags", response_model=CoachAthleteLinkResponse)
async def assign_tag(
    link_id: int,
    payload: CoachAthleteTagAssignRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthleteLinkResponse:
    link = await assign_tag_to_link(
        db=db,
        link_id=link_id,
        acting_user_id=user_id,
        payload=payload,
    )
    CRM_TAG_ASSIGNMENTS_TOTAL.inc()
    return link


@router.delete("/{link_id}/tags/{tag_id}", response_model=CoachAthleteLinkResponse)
async def remove_tag(
    link_id: int,
    tag_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthleteLinkResponse:
    return await remove_tag_from_link(
        db=db,
        link_id=link_id,
        tag_id=tag_id,
        acting_user_id=user_id,
    )
