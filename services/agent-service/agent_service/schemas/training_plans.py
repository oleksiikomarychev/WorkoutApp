from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# CalendarPlan schema
class CalendarPlanCreate(BaseModel):
    name: str
    duration_weeks: int
    
class CalendarPlan(CalendarPlanCreate):
    id: int
    
    class Config:
        from_attributes = True

# Mesocycle schema
class MesocycleCreate(BaseModel):
    name: str
    order_index: int
    weeks_count: int
    
class Mesocycle(MesocycleCreate):
    id: int
    calendar_plan_id: int
    
    class Config:
        from_attributes = True

# Microcycle schema
class MicrocycleCreate(BaseModel):
    name: str
    order_index: int
    days_count: int
    
class Microcycle(MicrocycleCreate):
    id: int
    mesocycle_id: int
    
    class Config:
        from_attributes = True

# PlanWorkout schema
class PlanWorkoutCreate(BaseModel):
    day_label: str
    order_index: int
    
class PlanWorkout(PlanWorkoutCreate):
    id: int
    microcycle_id: int
    
    class Config:
        from_attributes = True

# PlanExercise schema
class PlanExerciseCreate(BaseModel):
    exercise_definition_id: int
    exercise_name: str
    order_index: int
    
class PlanExercise(PlanExerciseCreate):
    id: int
    plan_workout_id: int
    
    class Config:
        from_attributes = True

# PlanSet schema
class PlanSetCreate(BaseModel):
    order_index: int
    intensity: Optional[int] = None
    effort: Optional[int] = None
    volume: Optional[int] = None
    
class PlanSet(PlanSetCreate):
    id: int
    plan_exercise_id: int
    
    class Config:
        from_attributes = True

# Full training plan schema
class TrainingPlan(BaseModel):
    calendar_plan: CalendarPlan
    mesocycles: List[Mesocycle]
    microcycles: List[Microcycle]
    workouts: List[PlanWorkout]
    exercises: List[PlanExercise]
    sets: List[PlanSet]


class TrainingPlanWithRationale(BaseModel):
    plan: TrainingPlan
    plan_rationale: Optional[str] = None


class TrainingPlanWithSummary(BaseModel):
    plan: TrainingPlan
    plan_summary: Optional[str] = None
