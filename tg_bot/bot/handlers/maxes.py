from aiogram import Router, html, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
import datetime

from bot.models.database import async_session
from bot.models.all_models import UserMax
from bot.services.workout_calculation import WorkoutCalculator

router = Router(name="maxes")

class AddMaxState(StatesGroup):
    waiting_for_weight = State()

COMMON_EXERCISES = [
    {"id": 35, "name_ua": "Присідання", "name_en": "Barbell Back Squat"},
    {"id": 15, "name_ua": "Жим лежачи", "name_en": "Barbell Bench Press"},
    {"id": 29, "name_ua": "Станова тяга", "name_en": "Deadlift"},
    {"id": 19, "name_ua": "Армійський жим", "name_en": "Overhead Press"},
    {"id": 24, "name_ua": "Підтягування", "name_en": "Pull-Up"},
    {"id": 49, "name_ua": "Бруси (Chest Dip)", "name_en": "Chest Dip"}
]

@router.message(Command("maxes"))
async def command_maxes_handler(message: Message) -> None:
    user_id = f"tg:{message.from_user.id}"
    
    async with async_session() as session:
        stmt = select(UserMax).where(UserMax.user_id == user_id).order_by(UserMax.date.desc())
        result = await session.execute(stmt)
        maxes = result.scalars().all()
        
    text = ""
    if not maxes:
        text = "У вас ще немає доданих максимумів.\n"
    else:
        lines = ["Ваші поточні максимуми:"]
        for m in maxes:
            # Map back to UA name if possible
            ex_info = next((e for e in COMMON_EXERCISES if e["id"] == m.exercise_id), None)
            name = ex_info["name_ua"] if ex_info else (m.exercise_name or f"Вправа {m.exercise_id}")
            lines.append(f"• {html.bold(name)}: {m.max_weight} кг x {m.rep_max} (1RM: {m.true_1rm or '?'} кг)")
        text = "\n".join(lines) + "\n\n"
        
    text += "Щоб додати новий максимум, введіть команду /add_max"
    await message.answer(text)

@router.message(Command("add_max"))
async def command_add_max(message: Message, state: FSMContext) -> None:
    builder = InlineKeyboardBuilder()
    for ex in COMMON_EXERCISES:
        builder.button(text=ex["name_ua"], callback_data=f"max_ex:{ex['id']}")
    builder.adjust(2)
    
    await message.answer("Оберіть вправу:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("max_ex:"))
async def process_exercise_selection(callback: CallbackQuery, state: FSMContext) -> None:
    ex_id = int(callback.data.split(":", 1)[1])
    ex_info = next((e for e in COMMON_EXERCISES if e["id"] == ex_id), None)
    
    if not ex_info:
        await callback.answer("Вправа не знайдена.", show_alert=True)
        return
        
    await state.update_data(exercise_id=ex_id, exercise_name=ex_info["name_en"], exercise_ua=ex_info["name_ua"])
    
    await callback.message.edit_text(f"Ви обрали: {html.bold(ex_info['name_ua'])}\nВведіть ваш піднятий 1ПМ (максимальна вага на 1 повторення у кг):")
    await state.set_state(AddMaxState.waiting_for_weight)
    await callback.answer()

@router.message(AddMaxState.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext) -> None:
    try:
        weight = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Будь ласка, введіть числове значення (наприклад: 100 або 100.5).")
        return
        
    data = await state.get_data()
    user_id = f"tg:{message.from_user.id}"
    ex_name = data['exercise_name']
    ex_id = data['exercise_id']
    ex_ua = data.get('exercise_ua', ex_name)
    
    # Reps and RPE are default 1 and 10 since it's a 1RM input
    reps = 1
    rpe = 10.0
    true_1rm = weight
    
    new_max = UserMax(
        user_id=user_id,
        exercise_id=ex_id,
        exercise_name=ex_name,
        max_weight=weight,
        rep_max=reps,
        true_1rm=true_1rm,
        date=datetime.date.today(),
    )
    
    async with async_session() as session:
        session.add(new_max)
        await session.commit()
        
    await state.clear()
    await message.answer(
        f"Максимум успішно додано!\n"
        f"Вправа: {html.bold(ex_ua)}\n"
        f"Ваш новий 1RM: {html.bold(f'{weight} кг')}"
    )

@router.message(Command("multi_maxes"))
async def command_multi_maxes(message: Message) -> None:
    # Format: /multi_maxes Присідання: 100, Жим лежачи: 80, Lat Pulldown: 50
    user_id = f"tg:{message.from_user.id}"
    
    text = message.text.replace("/multi_maxes", "").strip()
    if not text:
        await message.answer("Формат: /multi_maxes Присідання: 100, Жим лежачи: 80")
        return
        
    # Fetch all exercise names from DB
    from bot.services.plan_service import PlanService
    exercise_names = await PlanService.get_exercise_names()
    
    # Create a case-insensitive reverse lookup
    name_to_id = {name.lower().strip(): eid for eid, name in exercise_names.items()}
    # Add common exercises UA names as well
    for ce in COMMON_EXERCISES:
        name_to_id[ce["name_ua"].lower().strip()] = ce["id"]
        
    parts = text.split(",")
    added_names = []
    
    async with async_session() as session:
        for p in parts:
            if ":" not in p: continue
            name_part, weight_part = p.split(":", 1)
            name_part = name_part.strip()
            weight_part = weight_part.strip()
            
            try:
                weight = float(weight_part.replace(",", "."))
            except ValueError:
                continue
                
            ex_id = name_to_id.get(name_part.lower())
            if not ex_id:
                # Could not map exercise name
                continue
                
            # Get canonical name to store
            canonical_name = exercise_names.get(ex_id, name_part)
            
            # Check if exists, update or insert
            stmt = select(UserMax).where(UserMax.user_id == user_id, UserMax.exercise_id == ex_id)
            existing = (await session.execute(stmt)).scalars().first()
            if existing:
                existing.max_weight = weight
                existing.true_1rm = weight
                existing.date = datetime.date.today()
            else:
                new_max = UserMax(
                    user_id=user_id,
                    exercise_id=ex_id,
                    exercise_name=canonical_name,
                    max_weight=weight,
                    rep_max=1,
                    true_1rm=weight,
                    date=datetime.date.today(),
                )
                session.add(new_max)
            
            added_names.append(f"{name_part}: {weight} кг")
            
        await session.commit()
        
    if added_names:
        await message.answer("✅ Максимуми успішно оновлено:\n" + "\n".join(added_names) + "\n\nТепер ви можете перейти до /plans та застосувати план!")
    else:
        await message.answer("❌ Не вдалося розпізнати жодної ваги або вправи. Перевірте формат: Присідання: 100, Жим лежачи: 80")
