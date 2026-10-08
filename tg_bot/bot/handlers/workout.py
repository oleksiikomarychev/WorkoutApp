from aiogram import Router, html, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, asc
import datetime

from bot.models.database import async_session
from bot.models.all_models import (
    AppliedCalendarPlan, 
    Workout, 
    WorkoutExercise, 
    WorkoutSet
)

router = Router(name="workout")

@router.message(Command("workout"))
async def command_workout_handler(message: Message, state: FSMContext) -> None:
    user_id = f"tg:{message.from_user.id}"
    
    async with async_session() as session:
        # Find active plan
        stmt = select(AppliedCalendarPlan).where(
            AppliedCalendarPlan.user_id == user_id,
            AppliedCalendarPlan.is_active == True
        )
        plan = (await session.execute(stmt)).scalars().first()
        
        if not plan:
            await message.answer("У вас немає активного плану. Перейдіть до /plans щоб обрати.")
            return
            
        # Find next workout
        stmt = select(Workout).where(
            Workout.applied_plan_id == plan.id,
            Workout.completed_at == None
        ).order_by(asc(Workout.scheduled_for))
        
        workout = (await session.execute(stmt)).scalars().first()
        
        if not workout:
            await message.answer("Не знайдено наступних тренувань у вашому плані.")
            return
            
        # Load exercises and sets
        stmt = select(WorkoutExercise).where(WorkoutExercise.workout_id == workout.id).order_by(WorkoutExercise.order)
        exercises = (await session.execute(stmt)).scalars().all()
        
        if not exercises:
            await message.answer("Тренування порожнє.")
            return
            
        from bot.services.plan_service import PlanService
        exercise_names = await PlanService.get_exercise_names()
        
        # Build the workout text
        text_lines = [f"🏋️‍♂️ {html.bold('Ваше тренування:')} {workout.name}\n"]
        
        for idx, ex in enumerate(exercises):
            ex_name = exercise_names.get(ex.exercise_id, f"Вправа {ex.exercise_id}")
            text_lines.append(f"{idx + 1}. {html.bold(ex_name)}")
            
            stmt = select(WorkoutSet).where(WorkoutSet.exercise_id == ex.id).order_by(WorkoutSet.order_index)
            sets = (await session.execute(stmt)).scalars().all()
            
            for s_idx, s in enumerate(sets):
                target_weight = f"{s.working_weight} кг" if s.working_weight else "вага не розрахована"
                
                vol_text = f"{s.volume} повт." if s.volume else "Макс. повт. (AMRAP)"
                rpe_text = f" @ RPE {s.effort}" if s.effort else ""
                
                text_lines.append(f"   Підхід {s_idx + 1}: {vol_text}{rpe_text} -> {html.bold(target_weight)}")
            
            text_lines.append("") # Empty line between exercises
            
    # Add finish button
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Завершити тренування", callback_data=f"finish_workout:{workout.id}")
    
    await message.answer("\n".join(text_lines), reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("finish_workout:"))
async def finish_workout_callback(callback: CallbackQuery, state: FSMContext):
    workout_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        workout = await session.get(Workout, workout_id)
        if workout and workout.completed_at is None:
            workout.completed_at = datetime.datetime.now()
            workout.status = "completed"
            
            from bot.models.workouts import WorkoutSession
            w_session = WorkoutSession(
                user_id=workout.user_id,
                workout_id=workout.id,
                started_at=workout.scheduled_for or datetime.datetime.now(),
                finished_at=datetime.datetime.now(),
                status="completed",
                progress={} # Empty progress since we don't track it step-by-step in the bot
            )
            session.add(w_session)
            await session.commit()
            
            await callback.message.edit_text(callback.message.html_text + "\n\n🎉 Тренування завершено та збережено!", reply_markup=None)
        else:
            await callback.answer("Тренування вже завершено або не знайдено.", show_alert=True)
            
    await callback.answer()
