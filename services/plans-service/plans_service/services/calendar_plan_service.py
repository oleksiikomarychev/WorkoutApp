from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from ..models.calendar import CalendarPlan, Mesocycle, Microcycle, AppliedCalendarPlan, AppliedMesocycle, AppliedMicrocycle, AppliedWorkout, PlanWorkout, PlanExercise, PlanSet
from ..schemas.calendar_plan import CalendarPlanCreate, CalendarPlanUpdate, CalendarPlanResponse, PlanWorkoutCreate
from ..schemas.mesocycle import MicrocycleCreate
from ..schemas.schedule_item import ExerciseScheduleItem, ParamsSets
from fastapi import HTTPException, status

class CalendarPlanService:
    async def create_plan(db: AsyncSession, plan_data: CalendarPlanCreate) -> CalendarPlanResponse:
        try:
            # Create plan instance with only valid fields
            plan = CalendarPlan(
                name=plan_data.name,
                duration_weeks=plan_data.duration_weeks,
                is_active=True
            )
            db.add(plan)
            await db.flush()
            # Capture primary key before commit to avoid expired attribute access
            plan_id = plan.id

            # Process mesocycles
            for meso_idx, mesocycle_data in enumerate(plan_data.mesocycles):
                mesocycle = Mesocycle(
                    name=mesocycle_data.name,
                    order_index=meso_idx,
                    duration_weeks=mesocycle_data.duration_weeks,
                    calendar_plan_id=plan_id
                )
                db.add(mesocycle)
                await db.flush()

                # Process microcycles
                for micro_idx, microcycle_data in enumerate(mesocycle_data.microcycles):
                    microcycle = Microcycle(
                        name=microcycle_data.name,
                        order_index=micro_idx,
                        days_count=microcycle_data.days_count,
                        normalization_value=microcycle_data.normalization_value,
                        normalization_unit=microcycle_data.normalization_unit,
                        mesocycle_id=mesocycle.id
                    )
                    db.add(microcycle)
                    await db.flush()

                    # Process plan workouts
                    for workout_idx, workout_data in enumerate(microcycle_data.plan_workouts):
                        plan_workout = PlanWorkout(
                            day_label=workout_data.day_label,
                            order_index=workout_idx,
                            microcycle_id=microcycle.id
                        )
                        db.add(plan_workout)
                        await db.flush()

                        # Process exercises
                        for ex_idx, exercise_data in enumerate(workout_data.exercises):
                            # Validate exercise existence and get name
                            exercise_details = await CalendarPlanService._get_exercise_details(exercise_data.exercise_definition_id)
                            
                            plan_exercise = PlanExercise(
                                exercise_definition_id=exercise_data.exercise_definition_id,
                                exercise_name=exercise_details["name"],  # Store exercise name
                                order_index=ex_idx,
                                plan_workout_id=plan_workout.id
                            )
                            db.add(plan_exercise)
                            await db.flush()

                            # Process sets
                            for set_idx, set_data in enumerate(exercise_data.sets):
                                plan_set = PlanSet(
                                    order_index=set_idx,
                                    intensity=set_data.intensity,
                                    effort=set_data.effort,
                                    volume=set_data.volume,
                                    plan_exercise_id=plan_exercise.id
                                )
                                db.add(plan_set)
                        await db.flush()

            await db.commit()
            
            # Refresh the plan and load relationships
            stmt = select(CalendarPlan).options(
                selectinload(CalendarPlan.mesocycles).selectinload(Mesocycle.microcycles).selectinload(Microcycle.plan_workouts).selectinload(PlanWorkout.exercises).selectinload(PlanExercise.sets)
            ).where(CalendarPlan.id == plan_id)
            result = await db.execute(stmt)
            plan = result.scalars().first()
            
            if not plan:
                raise HTTPException(status_code=500, detail="Failed to load created plan")
            
            return CalendarPlanService._get_plan_response(plan)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    async def get_plan(db: AsyncSession, plan_id: int) -> Optional[CalendarPlanResponse]:
        try:
            # Load the entire plan structure
            stmt = select(CalendarPlan).options(
                selectinload(CalendarPlan.mesocycles)
                .selectinload(Mesocycle.microcycles)
                .selectinload(Microcycle.plan_workouts)
                .selectinload(PlanWorkout.exercises)
                .selectinload(PlanExercise.sets)
            ).where(CalendarPlan.id == plan_id)
            result = await db.execute(stmt)
            plan = result.scalars().first()
            
            if not plan:
                return None
                
            return CalendarPlanService._get_plan_response(plan)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get plan: {str(e)}"
            )

    async def get_all_plans(db: AsyncSession) -> List[CalendarPlanResponse]:
        try:
            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets)
                )
            )
            result = await db.execute(stmt)
            plans = result.scalars().unique().all()

            responses: List[CalendarPlanResponse] = []
            for plan in plans:
                try:
                    responses.append(CalendarPlanService._get_plan_response(plan))
                except Exception:
                    pass
            return responses
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch plans: {str(e)}",
            )

    async def update_plan(db: AsyncSession, plan_id: int, plan_data: CalendarPlanUpdate) -> CalendarPlanResponse:
        stmt = select(CalendarPlan).where(CalendarPlan.id == plan_id)
        result = await db.execute(stmt)
        plan = result.scalars().first()
        if not plan:
            raise ValueError("Plan not found or permission denied")
        for field, value in plan_data.model_dump(exclude_none=True).items():
            setattr(plan, field, value)

        await db.commit()
        return CalendarPlanService._get_plan_response(plan)

    async def delete_plan(db: AsyncSession, plan_id: int) -> None:
        try:
            # Load plan with related applied instances and hierarchy
            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets),
                    selectinload(CalendarPlan.applied_instances)
                    .selectinload(AppliedCalendarPlan.workouts),
                    selectinload(CalendarPlan.applied_instances)
                    .selectinload(AppliedCalendarPlan.mesocycles)
                    .selectinload(AppliedMesocycle.microcycles)
                    .selectinload(AppliedMicrocycle.workouts)
                )
                .where(CalendarPlan.id == plan_id)
            )
            result = await db.execute(stmt)
            plan = result.scalars().first()
            
            if plan:
                for mesocycle in plan.mesocycles:
                    for micro_cycle in mesocycle.microcycles:
                        for workout in micro_cycle.plan_workouts:
                            for exercise in workout.exercises:
                                for plan_set in exercise.sets:
                                    await db.delete(plan_set)
                                await db.delete(exercise)
                            await db.delete(workout)
                        await db.delete(micro_cycle)
                    await db.delete(mesocycle)

                # Delete applied instances and related data
                for applied_plan in plan.applied_instances:
                    for workout in applied_plan.workouts:
                        await db.delete(workout)
                    for applied_meso in applied_plan.mesocycles:
                        for applied_micro in applied_meso.microcycles:
                            for applied_workout in applied_micro.workouts:
                                await db.delete(applied_workout)
                            await db.delete(applied_micro)
                        await db.delete(applied_meso)
                    await db.delete(applied_plan)

                # Now delete the plan itself
                await db.delete(plan)
                await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    async def _get_exercise_details(exercise_definition_id: int) -> dict:
        import httpx
        try:
            # Call exercises service API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://exercises-service:8002/exercises/definitions/{exercise_definition_id}",
                    timeout=5.0
                )
            if response.status_code == 200:
                exercise = response.json()
                return {"id": exercise["id"], "name": exercise["name"]}
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Exercise with id {exercise_definition_id} not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error fetching exercise details"
                )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Exercises service unavailable"
            )

    @staticmethod
    def _get_plan_response(plan: CalendarPlan) -> CalendarPlanResponse:
        try:
            # Build the response
            mesocycles_list = []
            for mesocycle in plan.mesocycles:
                microcycles = []
                for microcycle in mesocycle.microcycles:
                    microcycles.append({
                        "id": microcycle.id,
                        "mesocycle_id": mesocycle.id,
                        "name": microcycle.name,
                        "plan_workouts": [
                            {
                                "id": pw.id,
                                "microcycle_id": microcycle.id,
                                "day_label": pw.day_label,
                                "order_index": pw.order_index,
                                "exercises": [
                                    {
                                        "id": pe.id,
                                        "exercise_definition_id": pe.exercise_definition_id,
                                        "exercise_name": pe.exercise_name,  # Include exercise name
                                        "order_index": pe.order_index,
                                        "plan_workout_id": pe.plan_workout_id,
                                        "sets": [
                                            {
                                                "id": ps.id,
                                                "order_index": ps.order_index,
                                                "intensity": ps.intensity,
                                                "effort": ps.effort,
                                                "volume": ps.volume,
                                                "plan_exercise_id": ps.plan_exercise_id
                                            } for ps in pe.sets
                                        ]
                                    } for pe in pw.exercises
                                ]
                            } for pw in microcycle.plan_workouts
                        ]
                    })
                mesocycles_list.append({
                    "id": mesocycle.id,
                    "name": mesocycle.name,
                    "order_index": mesocycle.order_index,
                    "microcycles": microcycles
                })
            response_data = {
                "id": getattr(plan, 'id', 0),
                "name": getattr(plan, 'name', ''),
                "duration_weeks": getattr(plan, 'duration_weeks', 0),
                "is_active": getattr(plan, 'is_active', True),
                "mesocycles": mesocycles_list
            }
            
            return CalendarPlanResponse.model_validate(response_data)
        except Exception as e:
            # Include IDs in fallback response
            mesocycles_list = []
            for meso in plan.mesocycles:
                microcycles_list = []
                for micro in meso.microcycles:
                    microcycles_list.append({
                        "id": micro.id,
                        "name": getattr(micro, 'name', ''),
                        "order_index": getattr(micro, 'order_index', 0),
                        "normalization_value": getattr(micro, 'normalization_value', None),
                        "normalization_unit": getattr(micro, 'normalization_unit', None),
                        "days_count": getattr(micro, 'days_count', 0)
                    })
                mesocycles_list.append({
                    "id": meso.id,
                    "name": getattr(meso, 'name', ''),
                    "order_index": getattr(meso, 'order_index', 0),
                    "weeks_count": getattr(meso, 'weeks_count', 0),
                    "microcycle_length_days": getattr(meso, 'microcycle_length_days', 0),
                    "microcycles": microcycles_list
                })
            
            return CalendarPlanResponse(
                id=getattr(plan, 'id', 0),
                name=getattr(plan, 'name', ''),
                duration_weeks=getattr(plan, 'duration_weeks', 0),
                is_active=getattr(plan, 'is_active', True),
                mesocycles=mesocycles_list
            )
