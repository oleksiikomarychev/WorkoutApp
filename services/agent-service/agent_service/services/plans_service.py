import httpx
import structlog

from ..config import settings
from ..schemas.training_plans import TrainingPlan

logger = structlog.get_logger(__name__)


def _to_calendar_plan_create_payload(plan: TrainingPlan) -> dict:
    micro_by_meso = {}
    for micro in plan.microcycles:
        micro_by_meso.setdefault(micro.mesocycle_id, []).append(micro)

    workouts_by_micro = {}
    for w in plan.workouts:
        workouts_by_micro.setdefault(w.microcycle_id, []).append(w)

    exercises_by_workout = {}
    for ex in plan.exercises:
        exercises_by_workout.setdefault(ex.plan_workout_id, []).append(ex)

    sets_by_ex = {}
    for s in plan.sets:
        sets_by_ex.setdefault(s.plan_exercise_id, []).append(s)

    mesocycles_payload = []

    meso_sorted = sorted(plan.mesocycles, key=lambda m: m.order_index)
    for meso in meso_sorted:
        micro_payload = []
        for micro in sorted(micro_by_meso.get(meso.id, []), key=lambda mc: mc.order_index):
            workouts_payload = []
            for w in sorted(workouts_by_micro.get(micro.id, []), key=lambda ww: ww.order_index):
                exercises_payload = []
                for ex in sorted(exercises_by_workout.get(w.id, []), key=lambda ee: ee.order_index):
                    sets_payload = []
                    for s in sorted(sets_by_ex.get(ex.id, []), key=lambda ss: (ss.order_index or 0)):
                        sets_payload.append(
                            {
                                "intensity": s.intensity,
                                "effort": s.effort,
                                "volume": s.volume,
                            }
                        )
                    exercises_payload.append(
                        {
                            "exercise_definition_id": ex.exercise_definition_id,
                            "sets": sets_payload,
                        }
                    )
                workouts_payload.append(
                    {
                        "day_label": w.day_label,
                        "order_index": w.order_index,
                        "exercises": exercises_payload,
                    }
                )
            micro_payload.append(
                {
                    "name": micro.name,
                    "days_count": micro.days_count,
                    "order_index": micro.order_index,
                    "normalization_value": None,
                    "normalization_unit": None,
                    "plan_workouts": workouts_payload,
                }
            )
        mesocycles_payload.append(
            {
                "name": meso.name,
                "duration_weeks": meso.weeks_count,
                "microcycles": micro_payload,
            }
        )

    return {
        "name": plan.calendar_plan.name,
        "duration_weeks": plan.calendar_plan.duration_weeks,
        "mesocycles": mesocycles_payload,
    }


async def save_plan_to_plans_service(plan: TrainingPlan, user_id: str):
    try:
        payload = _to_calendar_plan_create_payload(plan)
        headers = {"X-User-Id": user_id}
        base_url = settings.plans_service_url.rstrip("/")
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{base_url}/plans/calendar-plans/",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            plan_id = response.json().get("id")
            logger.info("plan_saved_to_plans_service", user_id=user_id, plan_id=plan_id)
            return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error("failed_to_save_plan_to_plans_service", user_id=user_id, error=str(e))
        return None
    except Exception as e:
        logger.error("failed_to_save_plan_to_plans_service_unexpected", user_id=user_id, error=str(e))
        return None
