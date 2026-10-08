import json
from pathlib import Path
from typing import Any
import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.models.all_models import (
    UserMax,
    CalendarPlan,
    AppliedCalendarPlan,
    AppliedMesocycle,
    AppliedMicrocycle,
    AppliedWorkout,
    AppliedPlanWorkout,
    PlanExercise,
    PlanSet
)
from bot.services.workout_calculation import WorkoutCalculator
from bot.services.rpe_calculations import get_intensity

class PlanService:
    @staticmethod
    def get_templates() -> list[dict[str, Any]]:
        # Read from real calendar_plans.json in services folder
        mock_path = Path(__file__).parent.parent.parent.parent / "services" / "calendar_plans.json"
        try:
            with open(mock_path, "r") as f:
                data = json.load(f)

                plans = data.get("plans", [])

                # Assign ID to each plan for the bot's UI if it doesn't have one
                for idx, plan in enumerate(plans):
                    if "id" not in plan:
                        plan["id"] = idx + 1

                return plans
        except Exception as e:
            print(f"Error loading plans: {e}")
            return []

    @staticmethod
    def get_template(template_id: int) -> dict[str, Any] | None:
        templates = PlanService.get_templates()
        for t in templates:
            if t["id"] == template_id:
                return t
        return None

    _exercise_names_cache: dict[int, str] = {}

    @classmethod
    async def get_exercise_names(cls) -> dict[int, str]:
        if cls._exercise_names_cache:
            return cls._exercise_names_cache

        import asyncpg
        import os

        db_url = os.getenv("EXERCISES_DATABASE_URL")
        if not db_url:
            return {}

        try:
            conn = await asyncpg.connect(db_url)
            rows = await conn.fetch("SELECT id, name FROM exercise_list")
            cls._exercise_names_cache = {row['id']: row['name'] for row in rows}
            await conn.close()
        except Exception as e:
            print(f"Failed to fetch exercise names from Postgres: {e}")

        return cls._exercise_names_cache

    @classmethod
    async def apply_template(cls, template_id: int, user_id: str, session: AsyncSession) -> tuple[bool, list[str]]:
        template = cls.get_template(template_id)
        if not template:
            return False, []

        # Find all required exercise IDs from template
        required_ex_ids = set()
        for meso_tpl in template.get("mesocycles", []):
            for micro_tpl in meso_tpl.get("microcycles", []):
                for workout_tpl in micro_tpl.get("plan_workouts", []):
                    for ex_tpl in workout_tpl.get("exercises", []):
                        required_ex_ids.add(ex_tpl.get("exercise_definition_id", 0))

        # Get user maxes
        stmt = select(UserMax).where(UserMax.user_id == user_id).order_by(UserMax.date.asc(), UserMax.id.asc())
        result = await session.execute(stmt)
        # Store by exercise_id
        user_maxes_by_id = {m.exercise_id: m.true_1rm for m in result.scalars().all() if m.true_1rm and m.exercise_id}

        # Check missing maxes against ALL exercises
        exercise_names = await cls.get_exercise_names()
        missing_max_names = []
        for req_id in required_ex_ids:
            if req_id not in user_maxes_by_id:
                name = exercise_names.get(req_id, f"Вправа {req_id}")
                missing_max_names.append(name)

        if missing_max_names:
            return False, missing_max_names

        rpe_table = WorkoutCalculator.get_rpe_table()

        # Create a CalendarPlan record first since AppliedCalendarPlan requires calendar_plan_id
        duration_weeks = template.get("duration_weeks", 4)

        # We need a root plan. Let's just make this plan its own root if we can't find one,
        # or we'll just query for an existing one. We will insert the template into DB.
        stmt_plan = select(CalendarPlan).where(CalendarPlan.name == template["name"])
        res_plan = await session.execute(stmt_plan)
        db_plan = res_plan.scalars().first()

        from sqlalchemy import insert, update
        if not db_plan:
            stmt = insert(CalendarPlan).values(
                name=template["name"],
                duration_weeks=duration_weeks,
                user_id="system",
                root_plan_id=-1
            ).returning(CalendarPlan.id)
            result = await session.execute(stmt)
            inserted_id = result.scalar()

            update_stmt = update(CalendarPlan).where(CalendarPlan.id == inserted_id).values(root_plan_id=inserted_id)
            await session.execute(update_stmt)

            db_plan = await session.get(CalendarPlan, inserted_id)

        # Create applied plan
        applied_plan = AppliedCalendarPlan(
            user_id=user_id,
            calendar_plan_id=db_plan.id,
            is_active=True,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(weeks=duration_weeks)
        )
        session.add(applied_plan)
        await session.flush() # get id

        current_date = datetime.date.today()

        for m_idx, meso_tpl in enumerate(template.get("mesocycles", [])):
            meso = AppliedMesocycle(
                applied_plan_id=applied_plan.id,
                order_index=m_idx + 1,
            )
            session.add(meso)
            await session.flush()

            for micro_idx, micro_tpl in enumerate(meso_tpl.get("microcycles", [])):
                micro = AppliedMicrocycle(
                    applied_mesocycle_id=meso.id,
                    order_index=micro_idx + 1,
                )
                session.add(micro)
                await session.flush()

                for w_idx, workout_tpl in enumerate(micro_tpl.get("plan_workouts", [])):
                    workout_date = current_date + datetime.timedelta(days=w_idx * 2) # spaced by 2 days

                    # Create the actual workout instance
                    from bot.models.workouts import Workout, WorkoutExercise, WorkoutSet

                    workout = Workout(
                        user_id=user_id,
                        name=workout_tpl.get("name") or f"Тренування {w_idx + 1}",
                        applied_plan_id=applied_plan.id,
                        plan_order_index=w_idx + 1,
                        scheduled_for=datetime.datetime.combine(workout_date, datetime.time()),
                        workout_type="generated"
                    )
                    session.add(workout)
                    await session.flush()

                    # Link to microcycle
                    app_workout = AppliedWorkout(
                        applied_microcycle_id=micro.id,
                        workout_id=workout.id,
                        order_index=w_idx + 1
                    )
                    session.add(app_workout)

                    # Link to applied plan
                    app_plan_workout = AppliedPlanWorkout(
                        applied_plan_id=applied_plan.id,
                        workout_id=workout.id,
                        order_index=w_idx + 1
                    )
                    session.add(app_plan_workout)
                    await session.flush()

                    for ex_idx, ex_tpl in enumerate(workout_tpl.get("exercises", [])):
                        ex_id = ex_tpl.get("exercise_definition_id", 0)

                        workout_ex = WorkoutExercise(
                            user_id=user_id,
                            workout_id=workout.id,
                            exercise_id=ex_id,
                            order=ex_idx + 1,
                            rest_seconds=ex_tpl.get("rest_seconds", 0),
                            notes=ex_tpl.get("notes")
                        )
                        session.add(workout_ex)
                        await session.flush()

                        for s_idx, set_tpl in enumerate(ex_tpl.get("sets", [])):
                            reps = set_tpl.get("volume", 0)
                            rpe = set_tpl.get("effort")
                            intensity = set_tpl.get("intensity")

                            target_weight = None

                            if ex_id in user_maxes_by_id:
                                true_1rm = user_maxes_by_id[ex_id]
                                if intensity:
                                    target_weight = round(true_1rm * (intensity / 100.0), 1)
                                elif rpe and reps and rpe_table:
                                    try:
                                        calc_intensity = get_intensity(rpe_table, volume=reps, effort=rpe)
                                        if calc_intensity:
                                            target_weight = round(true_1rm * (calc_intensity / 100.0), 1)
                                    except Exception:
                                        pass

                            workout_set = WorkoutSet(
                                exercise_id=workout_ex.id,
                                order_index=s_idx + 1,
                                intensity=intensity,
                                effort=rpe,
                                volume=reps,
                                working_weight=target_weight,
                                set_type=set_tpl.get("set_type", "normal")
                            )
                            session.add(workout_set)

                current_date += datetime.timedelta(days=7)

        await session.flush()
        await session.commit()
        return True, []
