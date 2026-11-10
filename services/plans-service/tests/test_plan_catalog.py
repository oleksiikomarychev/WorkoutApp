"""Run with CATALOG_TEST_DATABASE_URL pointing to a disposable PostgreSQL DB."""
import os

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from plans_service.dependencies import get_current_user_id, get_db
from plans_service.routers.calendar_plans import router
from plans_service.services.plan_catalog_service import search_catalog

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def db():
    url = os.getenv('CATALOG_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Requires disposable PostgreSQL via CATALOG_TEST_DATABASE_URL')
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
        # A temporary table shadows any persistent table and is dropped on close.
        await connection.execute(text('''CREATE TEMP TABLE calendar_plans (
            id int PRIMARY KEY, root_plan_id int, name text, notes text, user_id text,
            is_public boolean, duration_weeks int, primary_goal text,
            intended_experience_level text, intended_frequency_per_week int,
            session_duration_target_min int) ON COMMIT DROP'''))
        rows = [
            (1, 1, 'Starting Strength', 'Barbell training for novices', 'me', False, 10, 'strength', 'novice', 3),
            (2, 2, 'StrongLifts 5x5', 'Beginner program', 'other', True, 2, 'strength_hypertrophy', 'novice_to_intermediate', 3),
            (3, 3, 'Secret Strength', 'Barbell private', 'other', False, 99, 'secret_goal', 'secret_level', 14),
            (4, 1, 'Starting Strength variant', 'Barbell variant', 'me', False, 88, 'variant_goal', 'variant_level', 13),
            (5, 5, 'Силовая программа', 'Подготовка к соревнованиям', 'other', True, 12, 'strength', 'beginner-intermediate', 4),
            (6, 6, 'Mixed program', 'Training', 'me', False, 8, 'strength_hypertrophy', 'novice', 4),
            (7, 7, 'No metadata', None, 'me', False, 1, None, None, None),
            (8, 8, '100% effort', None, 'me', False, 3, 'strength', 'novice', 3),
        ]
        for row in rows:
            await connection.execute(text('''INSERT INTO calendar_plans
                (id,root_plan_id,name,notes,user_id,is_public,duration_weeks,primary_goal,
                 intended_experience_level,intended_frequency_per_week)
                VALUES (:id,:root,:name,:notes,:user,:public,:weeks,:goal,:level,:freq)'''),
                dict(zip(['id','root','name','notes','user','public','weeks','goal','level','freq'], row)))
        async with AsyncSession(bind=connection) as session:
            yield session
    await engine.dispose()


async def test_visibility_applies_to_items_totals_and_facets(db):
    page = await search_catalog(db, 'me')
    assert page.total == 6
    assert {p.id for p in page.items} == {1, 2, 5, 6, 7, 8}
    assert all(v.value not in ('secret_goal', 'variant_goal') for v in page.facets['goals'])
    assert all(v.value not in (99, 88) for v in page.facets['duration_weeks'])
    assert page.facets['goals'][0].count == 3


async def test_filters_keep_codes_distinct_and_facets_exclude_own_selection(db):
    page = await search_catalog(db, 'me', goals=['strength'], frequencies=[3])
    assert {p.id for p in page.items} == {1, 8}
    assert {v.value: v.count for v in page.facets['goals']} == {'strength': 2, 'strength_hypertrophy': 1}
    assert {v.value: v.count for v in page.facets['frequencies']} == {3: 2, 4: 1}
    page = await search_catalog(db, 'me', levels=['novice_to_intermediate'])
    assert [p.id for p in page.items] == [2]
    page = await search_catalog(db, 'me', levels=['beginner-intermediate'])
    assert [p.id for p in page.items] == [5]
    page = await search_catalog(db, 'me', duration_weeks=[2, 12], goals=['strength', 'strength_hypertrophy'])
    assert {p.id for p in page.items} == {2, 5}


async def test_search_title_notes_cyrillic_typo_and_literal_wildcards(db):
    for query, expected in [('barbell novices', {1}), ('соревнованиям', {5}),
                            ('StrongLift', {2}), ('Strenght', {1}), ('%', {8}), ('private', set())]:
        page = await search_catalog(db, 'me', q=query)
        assert {p.id for p in page.items} == expected, query
        assert page.total == len(expected)
    assert (await search_catalog(db, 'me', q="' OR 1=1 --")).total == 0


async def test_paging_is_stable_and_facets_cover_all_results(db):
    full = await search_catalog(db, 'me')
    first = await search_catalog(db, 'me', limit=2)
    second = await search_catalog(db, 'me', limit=2, offset=2)
    assert [p.id for p in first.items + second.items] == [p.id for p in full.items[:4]]
    assert first.total == second.total == full.total
    assert first.facets == second.facets == full.facets
    assert not hasattr(first.items[0], 'mesocycles')


async def test_http_route_contract_and_validation(db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_id] = lambda: 'me'
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/calendar-plans/catalog', params=[('duration_weeks', '2'), ('duration_weeks', '12')])
        assert response.status_code == 200
        assert response.json()['total'] == 2
        for params in [{'limit': 101}, {'offset': -1}, {'q': 'x' * 201}, {'frequencies': 0}, {'goals': 'x' * 33}]:
            assert (await client.get('/calendar-plans/catalog', params=params)).status_code == 422
