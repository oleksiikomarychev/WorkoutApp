from aiogram import Dispatcher
from .base import router as base_router
from .maxes import router as maxes_router
from .plans import router as plans_router
from .workout import router as workout_router
from .export import router as export_router

def setup_routers(dp: Dispatcher):
    dp.include_router(base_router)
    dp.include_router(maxes_router)
    dp.include_router(plans_router)
    dp.include_router(workout_router)
    dp.include_router(export_router)
