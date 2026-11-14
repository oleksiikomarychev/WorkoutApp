import asyncio
import os
import uuid

import pytest
from fastapi import HTTPException
from plans_service.services.applied_calendar_plan_service import AppliedCalendarPlanService
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_concurrent_apply_guard_serializes_check_and_creation():
    url = os.getenv("CONTRACT_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set CONTRACT_TEST_POSTGRES_URL to an isolated test PostgreSQL")
    schema = "contract_" + uuid.uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE TABLE applied_calendar_plans (id serial primary key, user_id text, is_active boolean)")
            )

        async def apply_once():
            async with factory() as db:
                try:
                    await AppliedCalendarPlanService(db, "same-user")._lock_and_check_active_plan(replace_active=False)
                    await asyncio.sleep(0.05)
                    await db.execute(
                        text("INSERT INTO applied_calendar_plans(user_id, is_active) VALUES ('same-user', true)")
                    )
                    await db.commit()
                    return 201
                except HTTPException as exc:
                    await db.rollback()
                    return exc.status_code

        assert sorted(await asyncio.gather(apply_once(), apply_once())) == [201, 409]
        async with factory() as db:
            assert (await db.execute(text("SELECT count(*) FROM applied_calendar_plans"))).scalar_one() == 1
            await AppliedCalendarPlanService(db, "same-user")._lock_and_check_active_plan(replace_active=True)
    finally:
        await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()
