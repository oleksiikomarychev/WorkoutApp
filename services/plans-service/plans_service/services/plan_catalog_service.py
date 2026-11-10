"""Search and disjunctive facets over visible original plans, without hierarchy loads."""
from collections.abc import Sequence

from sqlalchemy import case, func, literal_column, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.calendar import CalendarPlan
from ..schemas.plan_catalog import CatalogResponse

# Keep this expression identical to the migration. Simple preserves program
# names/acronyms in either alphabet without changing existing stored metadata.
SEARCH_VECTOR = "to_tsvector('simple'::regconfig, coalesce(name, '') || ' ' || coalesce(notes, ''))"
FACET_COLUMNS = {
    'duration_weeks': CalendarPlan.duration_weeks,
    'goals': CalendarPlan.primary_goal,
    'frequencies': CalendarPlan.intended_frequency_per_week,
    'levels': CalendarPlan.intended_experience_level,
}


async def search_catalog(
    db: AsyncSession, user_id: str, *, q: str = '',
    duration_weeks: Sequence[int] = (), goals: Sequence[str] = (),
    frequencies: Sequence[int] = (), levels: Sequence[str] = (),
    offset: int = 0, limit: int = 30,
) -> CatalogResponse:
    filters = dict(duration_weeks=duration_weeks, goals=goals, frequencies=frequencies, levels=levels)
    conditions = [
        or_(CalendarPlan.user_id == user_id, CalendarPlan.is_public.is_(True)),
        CalendarPlan.id == CalendarPlan.root_plan_id,
    ]
    q = q.strip()
    ranking = []
    if q:
        vector = literal_column(SEARCH_VECTOR)
        query = func.websearch_to_tsquery(literal_column("'simple'::regconfig"), q)
        fulltext = vector.op('@@')(query)
        # Bind the escaped pattern: LIKE wildcards in user input stay literal.
        escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        substring = CalendarPlan.name.ilike('%' + escaped + '%', escape='\\')
        matches = [fulltext, substring]
        if len(q) >= 3:
            await db.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = 0.4"))
            matches.append(CalendarPlan.name.op('%>')(q))
        conditions.append(or_(*matches))
        ranking = [
            case((func.lower(CalendarPlan.name) == q.lower(), 0), (substring, 1), (fulltext, 2), else_=3),
            func.ts_rank_cd(vector, query).desc(),
        ]

    def where(exclude=None):
        return conditions + [
            FACET_COLUMNS[key].in_(values)
            for key, values in filters.items() if values and key != exclude
        ]

    columns = [
        CalendarPlan.id, CalendarPlan.name, CalendarPlan.duration_weeks,
        CalendarPlan.primary_goal, CalendarPlan.intended_experience_level,
        CalendarPlan.intended_frequency_per_week, CalendarPlan.session_duration_target_min,
    ]
    items = (await db.execute(
        select(*columns).where(*where())
        .order_by(*ranking, func.lower(CalendarPlan.name), CalendarPlan.id)
        .offset(offset).limit(limit)
    )).mappings().all()
    total = (await db.execute(select(func.count()).select_from(CalendarPlan).where(*where()))).scalar_one()
    facets = {}
    for key, column in FACET_COLUMNS.items():
        # Ignore this facet's own selection so alternatives remain selectable.
        rows = (await db.execute(
            select(column.label('value'), func.count().label('count'))
            .where(*where(exclude=key), column.is_not(None))
            .group_by(column).order_by(column)
        )).mappings().all()
        facets[key] = [dict(row) for row in rows if row['value'] != '']
    return CatalogResponse(items=[dict(item) for item in items], total=total,
                           offset=offset, limit=limit, facets=facets)
