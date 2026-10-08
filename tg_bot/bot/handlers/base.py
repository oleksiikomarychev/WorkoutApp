from aiogram import Router, html
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="base")

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    text = (
        f"Привіт, {html.bold(message.from_user.full_name)}!\n\n"
        "Я WorkoutApp Telegram Bot. Мої можливості:\n"
        "💪 /maxes - Ваші повторні максимуми\n"
        "📅 /plans - Плани тренувань\n"
        "🏋️ /workout - Почати тренування\n"
        "💾 /export - Експортувати дані\n"
    )
    await message.answer(text)
