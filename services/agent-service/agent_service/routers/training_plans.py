from fastapi import APIRouter, Depends
from ..services.plan_generation import (
    generate_training_plan,
    generate_training_plan_with_rationale,
    generate_training_plan_with_summary,
)
from ..schemas.training_plans import TrainingPlan, TrainingPlanWithRationale, TrainingPlanWithSummary
from ..schemas.user_data import UserDataInput
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..services.plans_service import save_plan_to_plans_service
from ..services.rpe_rpc import notify_rpe_plan_created
from .. import models

router = APIRouter()

@router.post('/generate-plan/', response_model=TrainingPlan)
async def generate_plan(user_data: UserDataInput, db: Session = Depends(get_db)):
    """
    Generate a training plan based on user input and save it to the database.
    """
    plan = await generate_training_plan(user_data)
    # Save the plan
    save_generated_plan(db, plan)
    # Сохраняем в plans-service
    await save_plan_to_plans_service(plan)
    await notify_rpe_plan_created(plan)
    return plan


@router.post('/generate-plan-with-rationale/', response_model=TrainingPlanWithRationale)
async def generate_plan_with_rationale(user_data: UserDataInput, db: Session = Depends(get_db)):
    """Generate a training plan and return it along with the LLM rationale."""
    plan, rationale = await generate_training_plan_with_rationale(user_data)
    save_generated_plan(db, plan)
    await save_plan_to_plans_service(plan)
    await notify_rpe_plan_created(plan)
    return TrainingPlanWithRationale(plan=plan, plan_rationale=rationale)


@router.post('/generate-plan-with-summary/', response_model=TrainingPlanWithSummary)
async def generate_plan_with_summary(user_data: UserDataInput, db: Session = Depends(get_db)):
    """Generate a training plan and return it along with the in-model summary."""
    plan, summary = await generate_training_plan_with_summary(user_data)
    save_generated_plan(db, plan)
    await save_plan_to_plans_service(plan)
    await notify_rpe_plan_created(plan)
    return TrainingPlanWithSummary(plan=plan, plan_summary=summary)


def save_generated_plan(db: Session, plan: TrainingPlan):
    """
    Save a generated training plan to the database.
    """
    db_plan = models.GeneratedPlan(
        plan_data=plan.model_dump()
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan