import httpx
from ..schemas.training_plans import TrainingPlan
from ..config import settings
import logging

logger = logging.getLogger(__name__)


def _to_calendar_plan_create_payload(plan: TrainingPlan) -> dict:
    """Convert agent-service TrainingPlan to plans-service CalendarPlanCreate payload."""
    # Index for quick lookup
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

    # Build nested payload
    mesocycles_payload = []
    # Preserve order by mesocycle.order_index if available
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
                        sets_payload.append({
                            "intensity": s.intensity,
                            "effort": s.effort,
                            "volume": s.volume,
                        })
                    exercises_payload.append({
                        "exercise_definition_id": ex.exercise_definition_id,
                        "sets": sets_payload,
                    })
                workouts_payload.append({
                    "day_label": w.day_label,
                    "order_index": w.order_index,
                    "exercises": exercises_payload,
                })
            micro_payload.append({
                "name": micro.name,
                "days_count": micro.days_count,
                "order_index": micro.order_index,
                "normalization_value": None,
                "normalization_unit": None,
                "plan_workouts": workouts_payload,
            })
        mesocycles_payload.append({
            "name": meso.name,
            "duration_weeks": meso.weeks_count,
            "microcycles": micro_payload,
        })

    return {
        "name": plan.calendar_plan.name,
        "duration_weeks": plan.calendar_plan.duration_weeks,
        "mesocycles": mesocycles_payload,
    }

async def save_plan_to_plans_service(plan: TrainingPlan):
    """Отправляем план в plans-service (create calendar plan)."""
    try:
        payload = _to_calendar_plan_create_payload(plan)
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.plans_service_url}/plans/calendar-plans/",
                json=payload,
            )
            response.raise_for_status()
            logger.info("Plan saved to plans-service | id=%s", response.json().get("id"))
            return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Ошибка сохранения плана: {str(e)}")
        return None
