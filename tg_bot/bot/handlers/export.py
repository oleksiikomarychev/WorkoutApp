import json
import os
import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from sqlalchemy import select

from bot.models.database import async_session
from bot.models.all_models import (
    UserMax,
    Workout,
    WorkoutExercise,
    WorkoutSet
)

router = Router(name="export")

def alchemy_encoder(obj):
    """JSON encoder function for SQLAlchemy special classes."""
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    # add other types if needed
    return str(obj)

@router.message(Command("export"))
async def command_export_handler(message: Message) -> None:
    user_id = f"tg:{message.from_user.id}"
    
    export_data = {
        "user_id": user_id,
        "exported_at": datetime.datetime.now().isoformat(),
        "maxes": [],
        "workouts": []
    }
    
    async with async_session() as session:
        # Export Maxes
        stmt = select(UserMax).where(UserMax.user_id == user_id)
        maxes = (await session.execute(stmt)).scalars().all()
        for m in maxes:
            export_data["maxes"].append({
                "exercise_id": m.exercise_id,
                "exercise_name": m.exercise_name,
                "max_weight": m.max_weight,
                "rep_max": m.rep_max,
                "true_1rm": m.true_1rm,
                "date": alchemy_encoder(m.date)
            })
            
        # Export Workouts
        stmt = select(Workout).where(Workout.user_id == user_id)
        workouts = (await session.execute(stmt)).scalars().all()
        for w in workouts:
            w_dict = {
                "id": w.id,
                "name": w.name,
                "date": alchemy_encoder(w.date),
                "status": w.status,
                "exercises": []
            }
            
            stmt = select(WorkoutExercise).where(WorkoutExercise.workout_id == w.id)
            exercises = (await session.execute(stmt)).scalars().all()
            for ex in exercises:
                ex_dict = {
                    "id": ex.id,
                    "exercise_id": ex.exercise_id,
                    "exercise_name": ex.exercise_name,
                    "order_index": ex.order_index,
                    "sets": []
                }
                
                stmt = select(WorkoutSet).where(WorkoutSet.workout_exercise_id == ex.id)
                sets = (await session.execute(stmt)).scalars().all()
                for s in sets:
                    ex_dict["sets"].append({
                        "id": s.id,
                        "set_number": s.set_number,
                        "weight": s.weight,
                        "reps": s.reps,
                        "is_completed": s.is_completed
                    })
                    
                w_dict["exercises"].append(ex_dict)
            
            export_data["workouts"].append(w_dict)
            
    # Save to file
    file_name = f"export_{message.from_user.id}.json"
    file_path = f"/tmp/{file_name}"
    
    with open(file_path, "w") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
        
    doc = FSInputFile(file_path, filename="workout_data.json")
    await message.answer_document(
        document=doc, 
        caption="Ось ваш файл з даними. Завантажте його в основний застосунок."
    )
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)
