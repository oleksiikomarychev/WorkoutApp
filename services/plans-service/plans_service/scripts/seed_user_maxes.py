from __future__ import annotations

import argparse
from typing import Tuple

from ..database import SessionLocal, Base, engine
from ..models.exercises import ExerciseList
from ..models.user_max import UserMax


def _desired_values_for(ex_name: str, default_weight: int, default_rep_max: int) -> Tuple[int, int]:
    """Возвращает (max_weight, rep_max) для упражнения.
    Пока используем дефолтные значения; точные профили можно добавить позже.
    """
    presets = {
        "Приседания со штангой": (120, 6),
        "Жим лёжа": (100, 4),
        "Становая тяга": (140, 5),
        "Жим стоя (ОHP)": (60, 8),
        "Тяга штанги в наклоне": (80, 8),
        "Подтягивания": (15, 10),  # c доп. весом
        "Отжимания на брусьях": (20, 10), # c доп. весом
        "Разгибание на блоке": (40, 10),
        "Сгибание рук с гантелями": (16, 12),
    }

    for key, value in presets.items():
        if key in ex_name:
            return value

    return default_weight, default_rep_max


def seed_user_maxes(default_weight: int = 100, default_rep_max: int = 1, upsert: bool = True) -> None:
    """Создаёт (или обновляет) записи user_maxes для КАЖДОГО упражнения из exercise_list.

    - Если запись существует и upsert=True — обновляет значения.
    - Если запись существует и upsert=False — пропускает.
    - Если записи нет — создаёт.
    """
    # Создаём таблицы при необходимости (безопасно)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    created = 0
    updated = 0
    skipped = 0

    try:
        exercises = db.query(ExerciseList).all()
        for ex in exercises:
            want_weight, want_rep = _desired_values_for(ex.name, default_weight, default_rep_max)

            existing = db.query(UserMax).filter(UserMax.exercise_id == ex.id).first()
            if existing:
                if upsert:
                    changed = False
                    if existing.max_weight != want_weight:
                        existing.max_weight = want_weight
                        changed = True
                    if existing.rep_max != want_rep:
                        existing.rep_max = want_rep
                        changed = True
                    if changed:
                        updated += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
            else:
                db.add(UserMax(exercise_id=ex.id, max_weight=want_weight, rep_max=want_rep))
                created += 1

        db.commit()
        print(f"UserMax seeding finished: created={created}, updated={updated}, skipped={skipped}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed user_maxes for all exercises")
    parser.add_argument("--weight", type=int, default=100, help="Default 1RM weight to set for each exercise")
    parser.add_argument("--rep-max", type=int, default=1, help="Rep max to associate with the weight (e.g., 1 for 1RM)")
    parser.add_argument("--no-upsert", action="store_true", help="Do not update existing user_max records, only insert missing ones")
    args = parser.parse_args()

    seed_user_maxes(default_weight=args.weight, default_rep_max=args.rep_max, upsert=not args.no_upsert)


if __name__ == "__main__":
    main()
