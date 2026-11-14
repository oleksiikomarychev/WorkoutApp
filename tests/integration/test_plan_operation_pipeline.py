"""HTTP + PostgreSQL + Redis/Celery contract tests on isolated schemas.

Requires CONTRACT_TEST_POSTGRES_URL and CONTRACT_TEST_REDIS_URL. Never uses the
application database: every test creates and drops its own random schemas.
"""

import asyncio
import os
import socket
import threading
import time
import uuid
from datetime import datetime

import httpx
import pytest
import uvicorn
from celery.contrib.testing.worker import start_worker
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from plans_service import dependencies as pd
from plans_service import models as pm
from plans_service.celery_app import celery_app as plans_celery
from plans_service.routers import applied_calendar_plans as plan_routes
from plans_service.services.applied_calendar_plan_service import AppliedCalendarPlanService
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from workouts_service import database as wd
from workouts_service import dependencies as wdep
from workouts_service import models as wm
from workouts_service.celery_app import celery_app as workouts_celery
from workouts_service.routers import internal_purge, workout_generation, workouts
from workouts_service.tasks import workout_tasks as wt
from workouts_service.workout_calculation import WorkoutCalculator


class Server:
    def __init__(self, app):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.url = f"http://127.0.0.1:{self.sock.getsockname()[1]}"
        self.server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
        self.thread = threading.Thread(target=self.server.run, kwargs={"sockets": [self.sock]}, daemon=True)

    def start(self):
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        assert self.server.started

    def stop(self):
        self.server.should_exit = True
        self.thread.join(timeout=10)
        self.sock.close()
        assert not self.thread.is_alive()


@pytest.fixture
async def pipeline(monkeypatch):
    pg = os.getenv("CONTRACT_TEST_POSTGRES_URL")
    redis = os.getenv("CONTRACT_TEST_REDIS_URL")
    if not pg or not redis:
        pytest.skip("Isolated PostgreSQL and Redis URLs are required")
    token = uuid.uuid4().hex
    admin = create_async_engine(pg, poolclass=NullPool)
    schemas = ["plans_" + token, "workouts_" + token]
    engines = []
    factories = []
    servers = []
    worker = None
    config_keys = ["broker_url", "result_backend", "task_default_queue", "task_always_eager"]
    old_configs = [(app, {key: app.conf[key] for key in config_keys}) for app in (plans_celery, workouts_celery)]
    try:
        for schema, base in zip(schemas, (pm.Base, wd.Base)):
            async with admin.begin() as conn:
                await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            engine = create_async_engine(
                pg, poolclass=NullPool, connect_args={"server_settings": {"search_path": schema}}
            )
            engines.append(engine)
            async with engine.begin() as conn:
                await conn.run_sync(base.metadata.create_all)
            factories.append(async_sessionmaker(engine, expire_on_commit=False))
        pf, wf = factories

        async def plans_db():
            async with pf() as db:
                yield db

        async def workouts_db():
            async with wf() as db:
                yield db

        async def user():
            return "pipeline-user"

        async def no_maxes(*args, **kwargs):
            return []

        async def no_exercises(*args, **kwargs):
            return {}

        monkeypatch.setattr(AppliedCalendarPlanService, "_fetch_user_maxes_by_ids", no_maxes)
        monkeypatch.setattr(AppliedCalendarPlanService, "_ensure_exercises_present", no_exercises)
        monkeypatch.setattr(AppliedCalendarPlanService, "_fetch_exercise_metadata", no_exercises)
        monkeypatch.setattr(WorkoutCalculator, "_fetch_user_maxes", no_maxes)
        monkeypatch.setenv("INTERNAL_GATEWAY_SECRET", "pipeline-secret")
        monkeypatch.setenv("WORKOUT_GENERATION_CHUNK_SIZE", "1")
        monkeypatch.setattr(internal_purge.settings, "INTERNAL_GATEWAY_SECRET", "pipeline-secret")
        monkeypatch.setattr(wt, "AsyncSessionLocal", wf)

        # Worker sessions use the same isolated schema but a fresh engine per task.
        def task_engine(*args, **kwargs):
            engine = create_async_engine(
                pg, poolclass=NullPool, connect_args={"server_settings": {"search_path": schemas[0]}}
            )
            return engine, async_sessionmaker(engine, expire_on_commit=False)

        monkeypatch.setattr("backend_common.database.create_async_engine_and_session", task_engine)
        state = {
            "generate_calls": 0,
            "fail_generate": None,
            "fail_cleanup": 0,
            "cleanup_calls": 0,
            "start_first": False,
            "malformed_generate": False,
        }
        wa = FastAPI()
        wa.dependency_overrides[wd.get_db] = workouts_db
        wa.dependency_overrides[wdep.get_current_user_id] = user
        wa.include_router(workouts.router, prefix="/workouts")
        wa.include_router(workout_generation.router, prefix="/workouts")
        wa.include_router(internal_purge.router)

        @wa.middleware("http")
        async def inject_failure(request: Request, call_next):
            if request.url.path.endswith("/generate"):
                state["generate_calls"] += 1
                if state["generate_calls"] == state["fail_generate"]:
                    if state["start_first"]:
                        from workouts_service.services.session_service import SessionService

                        async with wf() as db:
                            workout = (await db.execute(select(wm.Workout).order_by(wm.Workout.id))).scalars().first()
                            session = await SessionService(db, user_id="pipeline-user").start_workout_session(
                                workout.id
                            )
                            session.progress = {"completed_sets": [1]}
                            await db.commit()
                    if state["malformed_generate"]:
                        return JSONResponse({"workout_ids": [42, 43]})
                    return JSONResponse({"detail": "injected generation failure"}, status_code=500)
            if request.url.path.endswith("/cleanup"):
                state["cleanup_calls"] += 1
                if state["fail_cleanup"]:
                    state["fail_cleanup"] -= 1
                    return JSONResponse({"detail": "injected cleanup outage"}, status_code=503)
            return await call_next(request)

        pa = FastAPI()
        pa.dependency_overrides[pd.get_db] = plans_db
        pa.dependency_overrides[pd.get_current_user_id] = user
        pa.include_router(plan_routes.router, prefix="/plans")
        for app in (wa, pa):
            server = Server(app)
            server.start()
            servers.append(server)
        monkeypatch.setenv("WORKOUTS_SERVICE_URL", servers[0].url)
        # Use the actual gateway HTTP proxy; identity verification is outside this contract.
        from gateway_app import main as gateway_main
        from gateway_app.routes.plans import plans_applied_router

        monkeypatch.setattr(gateway_main, "PLANS_SERVICE_URL", servers[1].url)
        ga = FastAPI()

        @ga.middleware("http")
        async def identity(request: Request, call_next):
            request.state.user = {"uid": "pipeline-user"}
            return await call_next(request)

        ga.include_router(plans_applied_router)
        gateway_server = Server(ga)
        gateway_server.start()
        servers.append(gateway_server)
        for app in (plans_celery, workouts_celery):
            app.conf.update(
                broker_url=redis, result_backend=redis, task_always_eager=False, task_default_queue="plans.tasks"
            )
        plans_celery.set_default()
        plans_celery.set_current()
        plans_celery.loader.import_default_modules()
        worker = start_worker(
            plans_celery,
            pool="solo",
            concurrency=1,
            perform_ping_check=False,
            queues=["plans.tasks", "workouts.tasks"],
            shutdown_timeout=15,
        )
        await asyncio.to_thread(worker.__enter__)

        async with pf() as db:
            plan = pm.CalendarPlan(id=1, root_plan_id=1, user_id="pipeline-user", name="Pipeline", duration_weeks=1)
            db.add(plan)
            await db.flush()
            meso = pm.Mesocycle(calendar_plan_id=1, name="M", duration_weeks=1, order_index=0)
            db.add(meso)
            await db.flush()
            micro = pm.Microcycle(mesocycle_id=meso.id, name="MC", days_count=2, order_index=0)
            db.add(micro)
            await db.flush()
            db.add_all(
                [
                    pm.PlanWorkout(
                        microcycle_id=micro.id,
                        day_label="Day 1",
                        order_index=0,
                        created_at=datetime(2026, 11, 1),
                        updated_at=datetime(2026, 11, 1),
                    ),
                    pm.PlanWorkout(
                        microcycle_id=micro.id,
                        day_label="Day 2",
                        order_index=1,
                        created_at=datetime(2026, 11, 1),
                        updated_at=datetime(2026, 11, 1),
                    ),
                ]
            )
            await db.commit()
        async with httpx.AsyncClient(base_url=servers[2].url, timeout=20) as client:
            yield client, pf, wf, state, servers[0].url
    finally:
        if worker is not None:
            await asyncio.to_thread(worker.__exit__, None, None, None)
        for server in reversed(servers):
            await asyncio.to_thread(server.stop)
        for app, config in old_configs:
            app.conf.update(config)
        for engine in engines:
            await engine.dispose()
        async with admin.begin() as conn:
            for schema in schemas:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await admin.dispose()


COMPUTE = {
    "compute_weights": False,
    "rounding_step": 2.5,
    "generate_workouts": True,
    "start_date": "2026-11-15T00:00:00Z",
}


async def wait_for(check, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = await check()
        if result:
            return result
        await asyncio.sleep(0.05)
    raise AssertionError("Pipeline condition did not complete in time")


@pytest.mark.asyncio
@pytest.mark.parametrize("cleanup_outage", [False, True])
@pytest.mark.parametrize("preserve_started", [False, True])
async def test_second_batch_failure_rolls_back_plan_and_cleans_workouts(
    pipeline, monkeypatch, cleanup_outage, preserve_started
):
    client, pf, wf, state, _ = pipeline
    state["fail_generate"] = 2
    state["fail_cleanup"] = 2 if cleanup_outage else 0
    state["start_first"] = preserve_started
    if cleanup_outage:
        cleanup_task = plans_celery.tasks["plans.cleanup_failed_application"]
        production_retry = cleanup_task.retry

        def immediate_retry(*args, **kwargs):
            kwargs["countdown"] = 0  # Exercise a real retry without the production minute-long delay.
            return production_retry(*args, **kwargs)

        monkeypatch.setattr(cleanup_task, "retry", immediate_retry)
    response = await client.post("/api/v1/plans/applied-plans/apply/1", params={"user_max_ids": "1"}, json=COMPUTE)
    assert response.status_code == 500
    assert state["generate_calls"] == 2

    async def cleaned():
        async with wf() as db:
            return not list(
                (await db.execute(select(wm.Workout).where(wm.Workout.applied_plan_id.is_not(None)))).scalars()
            )

    await wait_for(cleaned)
    assert state["cleanup_calls"] >= (3 if cleanup_outage else 1)
    async with wf() as db:
        remaining = list((await db.execute(select(wm.Workout))).scalars())
        assert len(remaining) == int(preserve_started)
        if preserve_started:
            assert remaining[0].applied_plan_id is None and remaining[0].plan_order_index is None
            progress = (await db.execute(select(wm.WorkoutSession.progress))).scalar_one()
            assert progress == {"completed_sets": [1]}
    async with pf() as db:
        assert not list((await db.execute(select(pm.AppliedCalendarPlan))).scalars())


@pytest.mark.asyncio
@pytest.mark.parametrize("async_replacement", [False, True])
async def test_explicit_replacement_retains_completed_history_sync_and_async(pipeline, async_replacement):
    client, pf, wf, state, _ = pipeline
    first = await client.post("/api/v1/plans/applied-plans/apply/1", params={"user_max_ids": "1"}, json=COMPUTE)
    assert first.status_code == 200, first.text
    old_id = first.json()["id"]
    async with wf() as db:
        workout = (await db.execute(select(wm.Workout).order_by(wm.Workout.id))).scalars().first()
        history_id = workout.id
        workout.status = "completed"
        workout.completed_at = datetime(2026, 11, 15)
        await db.commit()
    rejected = await client.post("/api/v1/plans/applied-plans/apply/1", params={"user_max_ids": "1"}, json=COMPUTE)
    assert rejected.status_code == 409
    path = "/api/v1/plans/applied-plans/apply" + ("-async" if async_replacement else "") + "/1"
    result = await client.post(path, params={"user_max_ids": "1", "replace_active": "true"}, json=COMPUTE)
    assert result.status_code == 200, result.text
    if async_replacement:
        task_id = result.json()["task_id"]

        async def done():
            response = await client.get(f"/api/v1/plans/applied-plans/tasks/{task_id}")
            data = response.json()
            return data if data.get("status") in ("SUCCESS", "FAILURE", "success", "failure") else None

        data = await wait_for(done)
        assert str(data["status"]).upper() == "SUCCESS", data
    async with pf() as db:
        plans = list((await db.execute(select(pm.AppliedCalendarPlan).order_by(pm.AppliedCalendarPlan.id))).scalars())
        assert len(plans) == 2
        assert plans[0].id == old_id and not plans[0].is_active
        assert plans[1].is_active
    async with wf() as db:
        history = await db.get(wm.Workout, history_id)
        assert history.status == "completed" and history.completed_at == datetime(2026, 11, 15)
        assert history.applied_plan_id == old_id


@pytest.mark.asyncio
async def test_async_mass_edit_and_shift_preserve_command_filters(pipeline):
    _, _, wf, _, workouts_url = pipeline
    dates = [datetime(2026, 11, 15), datetime(2026, 11, 16), datetime(2026, 11, 17)]
    async with wf() as db:
        for index, date in enumerate(dates):
            w = wm.Workout(
                user_id="pipeline-user",
                name=f"W{index}",
                applied_plan_id=9,
                plan_order_index=index,
                status="completed" if index == 2 else "pending",
                scheduled_for=date,
                workout_type="generated",
            )
            db.add(w)
            await db.flush()
            ex = wm.WorkoutExercise(user_id="pipeline-user", workout_id=w.id, exercise_id=1)
            db.add(ex)
            await db.flush()
            db.add(wm.WorkoutSet(exercise_id=ex.id, volume=5, working_weight=10))
        await db.commit()

    async def finished(task_id):
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=plans_celery)
        if not result.ready():
            return None
        assert result.successful(), str(result.result)
        return result.result

    async with httpx.AsyncClient(base_url=workouts_url, timeout=20) as client:
        mass = {
            "mode": "apply",
            "filter": {"plan_order_indices": [0, 2], "only_future": False},
            "actions": {"set_weight": 35},
        }
        response = await client.post("/workouts/applied-plans/9/mass-edit-sets-async", json=mass)
        assert response.status_code == 200, response.text
        task_id = response.json()["task_id"]
        await wait_for(lambda: finished(task_id))
        async with wf() as db:
            weights = list(
                (await db.execute(select(wm.WorkoutSet.working_weight).order_by(wm.WorkoutSet.id))).scalars()
            )
            assert weights == [35, 10, 10]

        shift = {
            "from_date": "2026-11-15T00:00:00Z",
            "to_date": "2026-11-15T23:59:00Z",
            "days": 3,
            "only_future": False,
            "mode": "preview",
        }
        response = await client.post("/workouts/applied-plans/9/shift-schedule-async", json=shift)
        assert response.status_code == 200, response.text
        task_id = response.json()["task_id"]
        result = await wait_for(lambda: finished(task_id))
        assert result["summary"]["mode"] == "preview"
        async with wf() as db:
            actual = list((await db.execute(select(wm.Workout.scheduled_for).order_by(wm.Workout.id))).scalars())
            assert actual == dates
        shift["mode"] = "apply"
        response = await client.post("/workouts/applied-plans/9/shift-schedule-async", json=shift)
        assert response.status_code == 200, response.text
        task_id = response.json()["task_id"]
        await wait_for(lambda: finished(task_id))
        async with wf() as db:
            actual = list((await db.execute(select(wm.Workout.scheduled_for).order_by(wm.Workout.id))).scalars())
            assert actual == [datetime(2026, 11, 18), dates[1], dates[2]]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_mass_edit_failure_has_no_partial_write_over_http_or_worker(pipeline, monkeypatch, async_mode):
    from workouts_service.services.exercise_instance_service import ExerciseInstanceService

    _, _, wf, _, url = pipeline
    async with wf() as db:
        w = wm.Workout(user_id="pipeline-user", name="Rollback", applied_plan_id=9, plan_order_index=0)
        db.add(w)
        await db.flush()
        ex = wm.WorkoutExercise(user_id="pipeline-user", workout_id=w.id, exercise_id=1)
        db.add(ex)
        await db.flush()
        db.add_all(
            [wm.WorkoutSet(exercise_id=ex.id, working_weight=10), wm.WorkoutSet(exercise_id=ex.id, working_weight=20)]
        )
        await db.commit()
    original = ExerciseInstanceService.update_set
    calls = 0

    async def fail_second(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected second-set failure")
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(ExerciseInstanceService, "update_set", fail_second)
    # Observe the failed attempt without waiting for a production retry countdown.
    monkeypatch.setattr(plans_celery.tasks["workouts.applied_plan_mass_edit_sets"], "max_retries", 0)
    path = "/workouts/applied-plans/9/mass-edit-sets" + ("-async" if async_mode else "")
    payload = {
        "mode": "apply",
        "filter": {"plan_order_indices": [0], "only_future": False},
        "actions": {"set_weight": 50},
    }
    async with httpx.AsyncClient(base_url=url, timeout=20) as client:
        response = await client.post(path, json=payload)
        if async_mode:
            assert response.status_code == 200, response.text
            from celery.result import AsyncResult

            task_id = response.json()["task_id"]

            async def failed():
                task = AsyncResult(task_id, app=plans_celery)
                return task.failed()

            await wait_for(failed)
        else:
            assert response.status_code == 500, response.text
    async with wf() as db:
        weights = list((await db.execute(select(wm.WorkoutSet.working_weight).order_by(wm.WorkoutSet.id))).scalars())
        assert weights == [10, 20]


@pytest.mark.asyncio
async def test_schedule_shift_skips_workout_completed_while_waiting_for_lock(pipeline):
    _, _, wf, _, url = pipeline
    original_date = datetime(2026, 11, 15)
    async with wf() as db:
        w = wm.Workout(
            user_id="pipeline-user", name="Concurrent", applied_plan_id=9, scheduled_for=original_date, status="pending"
        )
        db.add(w)
        await db.commit()
        workout_id = w.id
    async with wf() as completing, httpx.AsyncClient(base_url=url, timeout=20) as client:
        w = (
            await completing.execute(select(wm.Workout).where(wm.Workout.id == workout_id).with_for_update())
        ).scalar_one()
        w.status = "completed"
        await completing.flush()
        request = asyncio.create_task(
            client.post(
                "/workouts/applied-plans/9/shift-schedule",
                json={"from_date": "2026-11-01T00:00:00Z", "days": 5, "only_future": False, "mode": "apply"},
            )
        )
        await asyncio.sleep(0.15)
        assert not request.done(), "Shift must wait for the row lock protecting completion"
        await completing.commit()
        response = await request
        assert response.status_code == 200, response.text
        assert response.json()["workouts_shifted"] == 0
    async with wf() as db:
        w = await db.get(wm.Workout, workout_id)
        assert w.status == "completed" and w.scheduled_for == original_date


@pytest.mark.asyncio
async def test_malformed_generation_success_does_not_commit_partial_plan(pipeline):
    client, pf, wf, state, _ = pipeline
    state["fail_generate"] = 2
    state["malformed_generate"] = True
    response = await client.post("/api/v1/plans/applied-plans/apply/1", params={"user_max_ids": "1"}, json=COMPUTE)
    assert response.status_code == 500
    async with pf() as db:
        assert not list((await db.execute(select(pm.AppliedCalendarPlan))).scalars())
    async with wf() as db:
        assert not list((await db.execute(select(wm.Workout))).scalars())


@pytest.mark.asyncio
async def test_async_application_domain_error_is_failure_not_success(pipeline):
    client, pf, _, _, _ = pipeline
    response = await client.post(
        "/api/v1/plans/applied-plans/apply-async/999", params={"user_max_ids": "1"}, json=COMPUTE
    )
    assert response.status_code == 200, response.text
    task_id = response.json()["task_id"]

    async def terminal():
        data = (await client.get(f"/api/v1/plans/applied-plans/tasks/{task_id}")).json()
        return data if data["status"] in ("SUCCESS", "FAILURE") else None

    result = await wait_for(terminal)
    assert result["status"] == "FAILURE", result
    async with pf() as db:
        assert not list((await db.execute(select(pm.AppliedCalendarPlan))).scalars())
