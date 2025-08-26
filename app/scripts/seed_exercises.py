from __future__ import annotations

import argparse
from typing import List, Dict

from app.database import SessionLocal, Base, engine
from app.models.exercises import ExerciseList


DEFAULT_EXERCISES: List[Dict[str, str | None]] = [
    {"name": "Приседания со штангой", "muscle_group": "Ноги", "equipment": "Штанга"},
    {"name": "Жим лёжа", "muscle_group": "Грудь", "equipment": "Штанга"},
    {"name": "Становая тяга", "muscle_group": "Спина", "equipment": "Штанга"},
    {"name": "Жим стоя (ОHP)", "muscle_group": "Плечи", "equipment": "Штанга"},
    {"name": "Тяга штанги в наклоне", "muscle_group": "Спина", "equipment": "Штанга"},
    {"name": "Подтягивания", "muscle_group": "Спина", "equipment": "Собственный вес"},
    {"name": "Отжимания на брусьях", "muscle_group": "Грудь/Трицепс", "equipment": "Собственный вес"},
    {"name": "Сгибание рук с гантелями", "muscle_group": "Бицепс", "equipment": "Гантели"},
    {"name": "Разгибание на блоке", "muscle_group": "Трицепс", "equipment": "Кроссовер"},
    {"name": "Жим ногами", "muscle_group": "Ноги", "equipment": "Тренажёр"},
    {"name": "Выпады с гантелями", "muscle_group": "Ноги", "equipment": "Гантели"},
    {"name": "Румынская тяга", "muscle_group": "Бёдра", "equipment": "Штанга"},
    {"name": "Ягодичный мост", "muscle_group": "Ягодицы", "equipment": "Штанга"},
    {"name": "Тяга вертикального блока", "muscle_group": "Спина", "equipment": "Кроссовер"},
    {"name": "Тяга горизонтального блока", "muscle_group": "Спина", "equipment": "Тренажёр"},
    {"name": "Жим на наклонной скамье", "muscle_group": "Грудь", "equipment": "Штанга"},
    {"name": "Сведения гантелей (флай)", "muscle_group": "Грудь", "equipment": "Гантели"},
    {"name": "Махи в стороны", "muscle_group": "Плечи", "equipment": "Гантели"},
    {"name": "Планка", "muscle_group": "Кор", "equipment": "Собственный вес"},
    {"name": "Подъёмы ног в висе", "muscle_group": "Кор", "equipment": "Собственный вес"},
]


def seed(exercises: List[Dict[str, str | None]] = DEFAULT_EXERCISES, upsert: bool = True) -> None:
    """Заполняет таблицу exercise_list начальными данными.

    - Если upsert=True: обновляет muscle_group/equipment по совпадению name
    - Если upsert=False: добавляет только отсутствующие (по name)
    """
    # Создаём таблицы при необходимости (безопасно)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    created = 0
    updated = 0
    skipped = 0

    try:
        for e in exercises:
            name = e.get("name")
            if not name:
                continue

            existing = db.query(ExerciseList).filter(ExerciseList.name == name).first()
            if existing:
                if upsert:
                    changed = False
                    mg = e.get("muscle_group")
                    eq = e.get("equipment")
                    if mg is not None and existing.muscle_group != mg:
                        existing.muscle_group = mg
                        changed = True
                    if eq is not None and existing.equipment != eq:
                        existing.equipment = eq
                        changed = True
                    if changed:
                        updated += 1
                else:
                    skipped += 1
            else:
                db.add(ExerciseList(
                    name=name,
                    muscle_group=e.get("muscle_group"),
                    equipment=e.get("equipment"),
                ))
                created += 1

        db.commit()
        print(f"Exercises seeding finished: created={created}, updated={updated}, skipped={skipped}")
    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed exercises into the database")
    parser.add_argument("--no-upsert", action="store_true", help="Do not update existing records, only insert missing ones")
    args = parser.parse_args()

    seed(upsert=not args.no_upsert)


if __name__ == "__main__":
    main()
