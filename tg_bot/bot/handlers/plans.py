from aiogram import Router, html, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from bot.models.database import async_session
from bot.models.all_models import AppliedCalendarPlan, AppliedPlanWorkout, CalendarPlan, Workout
from bot.services.plan_service import PlanService

router = Router(name="plans")

@router.message(Command("plans"))
async def command_plans_handler(message: Message) -> None:
    user_id = f"tg:{message.from_user.id}"
    
    async with async_session() as session:
        stmt = select(AppliedCalendarPlan, CalendarPlan.name).join(
            CalendarPlan, AppliedCalendarPlan.calendar_plan_id == CalendarPlan.id
        ).where(
            AppliedCalendarPlan.user_id == user_id,
            AppliedCalendarPlan.is_active == True
        )
        result = await session.execute(stmt)
        row = result.first()
        
    if row:
        active_plan, plan_name = row
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Відмовитись від плану", callback_data=f"drop_plan:{active_plan.id}")
        
        await message.answer(
            f"💪 Ваш поточний активний план: {html.bold(plan_name)}\n"
            f"📅 Дата початку: {active_plan.start_date}\n"
            f"🏁 Дата завершення: {active_plan.end_date}\n\n"
            f"Щоб переглянути деталі або почати тренування, скористайтеся /workout",
            reply_markup=builder.as_markup()
        )
        return
        
    templates = PlanService.get_templates()
    if not templates:
        await message.answer("На жаль, наразі немає доступних планів.")
        return
        
    keyboard_builder = []
    text = "У вас немає активного плану. Доступні шаблони:\n\n"
    
    for t in templates:
        desc = t.get('description') or t.get('primary_goal') or 'Без опису'
        text += f"• {html.bold(t['name'])} ({t['duration_weeks']} тижнів)\n  {desc}\n\n"
        keyboard_builder.append([
            InlineKeyboardButton(text=f"Застосувати: {t['name']}", callback_data=f"apply_plan_{t['id']}")
        ])
        
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_builder)
    await message.answer(text, reply_markup=reply_markup)

@router.callback_query(F.data.startswith("apply_plan_"))
async def callback_apply_plan(callback: CallbackQuery):
    template_id = int(callback.data.split("_")[-1])
    user_id = f"tg:{callback.from_user.id}"
    
    async with async_session() as session:
        success, missing_maxes = await PlanService.apply_template(template_id, user_id, session)
        
    if success:
        await callback.message.edit_text(
            "✅ План успішно застосовано!\n\n"
            "Ваги для вправ були розраховані на основі ваших повторних максимумів.\n"
            "Використовуйте /workout щоб розпочати тренування."
        )
    elif missing_maxes:
        # Prompt user to provide maxes
        await callback.message.edit_text(
            "⚠️ Для того, щоб ваги були розраховані правильно, потрібно додати наступні максимуми (1ПМ). "
            "Скопіюйте текст нижче, підставте свої ваги у кг і відправте мені повідомлення:"
        )
        missing_text = ", ".join(f"{name}: 0" for name in missing_maxes)
        await callback.message.answer(f"/multi_maxes {missing_text}")
    else:
        await callback.message.edit_text("❌ Помилка при застосуванні плану. Спробуйте пізніше.")
        
    await callback.answer()

@router.callback_query(F.data.startswith("drop_plan:"))
async def callback_drop_plan(callback: CallbackQuery):
    applied_plan_id = int(callback.data.split(":")[1])
    user_id = f"tg:{callback.from_user.id}"
    
    async with async_session() as session:
        stmt = select(AppliedCalendarPlan).where(
            AppliedCalendarPlan.id == applied_plan_id,
            AppliedCalendarPlan.user_id == user_id
        )
        plan = (await session.execute(stmt)).scalars().first()
        if plan:
            plan.is_active = False
            
            # Optional: Cancel pending workouts
            from sqlalchemy import update
            stmt_update = update(Workout).where(
                Workout.applied_plan_id == plan.id,
                Workout.completed_at == None
            ).values(status="cancelled")
            await session.execute(stmt_update)
            
            await session.commit()
            await callback.message.edit_text("✅ Ви успішно відмовилися від поточного плану.\nВведіть /plans, щоб обрати новий.")
        else:
            await callback.answer("План не знайдено або він вже неактивний.", show_alert=True)
            
    await callback.answer()
