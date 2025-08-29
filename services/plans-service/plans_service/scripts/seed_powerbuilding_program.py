from __future__ import annotations

import argparse
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from ..database import SessionLocal, Base, engine
from ..models.calendar import CalendarPlan, Mesocycle, Microcycle
from ..models.exercises import ExerciseList


# --- Workout Day Templates ---


def _get_exercise_id(db: Session, name: str) -> int | None:
    """Helper to find an exercise ID by its name."""
    ex = db.query(ExerciseList).filter(ExerciseList.name.ilike(f"%{name}%")).first()
    return ex.id if ex else None


def _create_exercise(ex_id: int, sets: List[Dict[str, int]]) -> Dict[str, Any]:
    """Creates a single exercise entry for the schedule."""
    return {"exercise_id": ex_id, "sets": sets}


def get_upper_body_hypertrophy_day(db: Session) -> List[Dict[str, Any]]:
    """Template for Upper Body Hypertrophy day."""
    exercises = [
        _create_exercise(
            _get_exercise_id(db, "Жим лёжа"),
            [
                {"intensity": 70, "volume": 10, "effort": 7},
                {"intensity": 75, "volume": 8, "effort": 8},
                {"intensity": 75, "volume": 8, "effort": 8},
                {"intensity": 75, "volume": 8, "effort": 9},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Тяга штанги в наклоне"),
            [
                {"intensity": 70, "volume": 10, "effort": 8},
                {"intensity": 70, "volume": 10, "effort": 8},
                {"intensity": 70, "volume": 10, "effort": 9},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Жим стоя"),
            [
                {"intensity": 65, "volume": 12, "effort": 8},
                {"intensity": 65, "volume": 12, "effort": 9},
                {"intensity": 65, "volume": 12, "effort": 9},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Подтягивания"),
            [
                {
                    "intensity": 0,
                    "volume": 10,
                    "effort": 9,
                },  # Bodyweight or with assistance
                {"intensity": 0, "volume": 10, "effort": 9},
                {"intensity": 0, "volume": 10, "effort": 10},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Разгибание на блоке"),
            [
                {"intensity": 60, "volume": 15, "effort": 9},
                {"intensity": 60, "volume": 15, "effort": 10},
            ],
        ),
    ]
    return [e for e in exercises if e["exercise_id"] is not None]


def get_lower_body_hypertrophy_day(db: Session) -> List[Dict[str, Any]]:
    """Template for Lower Body Hypertrophy day."""
    exercises = [
        _create_exercise(
            _get_exercise_id(db, "Приседания со штангой"),
            [
                {"intensity": 70, "volume": 10, "effort": 7},
                {"intensity": 75, "volume": 8, "effort": 8},
                {"intensity": 75, "volume": 8, "effort": 8},
                {"intensity": 75, "volume": 8, "effort": 9},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Румынская тяга"),
            [
                {"intensity": 65, "volume": 12, "effort": 8},
                {"intensity": 65, "volume": 12, "effort": 8},
                {"intensity": 65, "volume": 12, "effort": 9},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Жим ногами"),
            [
                {"intensity": 70, "volume": 15, "effort": 9},
                {"intensity": 70, "volume": 15, "effort": 9},
                {"intensity": 70, "volume": 15, "effort": 10},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Сгибание ног"),
            [
                {"intensity": 60, "volume": 15, "effort": 9},
                {"intensity": 60, "volume": 15, "effort": 10},
            ],
        ),
    ]
    return [e for e in exercises if e["exercise_id"] is not None]


def get_upper_body_strength_day(db: Session) -> List[Dict[str, Any]]:
    """Template for Upper Body Strength day."""
    exercises = [
        _create_exercise(
            _get_exercise_id(db, "Жим лёжа"),
            [
                {"intensity": 80, "volume": 5, "effort": 8},
                {"intensity": 85, "volume": 3, "effort": 9},
                {"intensity": 85, "volume": 3, "effort": 9},
                {"intensity": 85, "volume": 3, "effort": 9},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Тяга штанги в наклоне"),
            [
                {"intensity": 80, "volume": 6, "effort": 8},
                {"intensity": 80, "volume": 6, "effort": 8},
                {"intensity": 80, "volume": 6, "effort": 9},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Жим стоя"),
            [
                {"intensity": 75, "volume": 5, "effort": 8},
                {"intensity": 75, "volume": 5, "effort": 9},
                {"intensity": 75, "volume": 5, "effort": 9},
            ],
        ),
    ]
    return [e for e in exercises if e["exercise_id"] is not None]


def get_lower_body_strength_day(db: Session) -> List[Dict[str, Any]]:
    """Template for Lower Body Strength day."""
    exercises = [
        _create_exercise(
            _get_exercise_id(db, "Приседания со штангой"),
            [
                {"intensity": 80, "volume": 5, "effort": 8},
                {"intensity": 85, "volume": 3, "effort": 9},
                {"intensity": 85, "volume": 3, "effort": 9},
                {"intensity": 85, "volume": 3, "effort": 9},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Становая тяга"),
            [
                {"intensity": 80, "volume": 5, "effort": 8},
                {"intensity": 85, "volume": 3, "effort": 9},
            ],
        ),
    ]
    return [e for e in exercises if e["exercise_id"] is not None]


def get_deload_day(db: Session) -> List[Dict[str, Any]]:
    """Template for a Deload day."""
    exercises = [
        _create_exercise(
            _get_exercise_id(db, "Жим лёжа"),
            [
                {"intensity": 50, "volume": 5, "effort": 4},
                {"intensity": 50, "volume": 5, "effort": 4},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Приседания со штангой"),
            [
                {"intensity": 50, "volume": 5, "effort": 4},
                {"intensity": 50, "volume": 5, "effort": 4},
            ],
        ),
        _create_exercise(
            _get_exercise_id(db, "Тяга блока"),
            [
                {"intensity": 50, "volume": 8, "effort": 4},
                {"intensity": 50, "volume": 8, "effort": 4},
            ],
        ),
    ]
    return [e for e in exercises if e["exercise_id"] is not None]


# --- Main Seeding Function ---


def seed_program(plan_name: str, drop_existing: bool = True) -> None:
    """Creates a detailed, multi-phase training program."""
    db = SessionLocal()
    try:
        if drop_existing:
            existing_plan = (
                db.query(CalendarPlan).filter(CalendarPlan.name == plan_name).first()
            )
            if existing_plan:
                db.delete(existing_plan)
                db.commit()
                print(f"Deleted existing plan: '{plan_name}'")

        # --- Define Program Structure ---
        mesocycles_data = [
            {"name": "Гипертрофия", "microcycles_count": 12, "days_per_micro": 8},
            {
                "name": "Силовая интенсификация",
                "microcycles_count": 6,
                "days_per_micro": 6,
            },
            {"name": "Делоад", "microcycles_count": 3, "days_per_micro": 7},
        ]

        new_plan = CalendarPlan(
            name=plan_name,
            schedule={},  # Top-level schedule is now deprecated
            duration_weeks=sum(
                m["microcycles_count"] * m["days_per_micro"] // 7
                for m in mesocycles_data
            ),
            mesocycles=[],
        )

        # --- Build Mesocycles and Microcycles ---
        for meso_idx, meso_data in enumerate(mesocycles_data):
            meso = Mesocycle(
                name=meso_data["name"], order_index=meso_idx, microcycles=[]
            )

            for micro_idx in range(meso_data["microcycles_count"]):
                schedule = {}
                if meso_data["name"] == "Гипертрофия":
                    # 8-day cycle: U/L/R/U/L/R/U/L
                    schedule = {
                        "day_1": get_upper_body_hypertrophy_day(db),
                        "day_2": get_lower_body_hypertrophy_day(db),
                        "day_3": [],
                        "day_4": get_upper_body_hypertrophy_day(db),
                        "day_5": get_lower_body_hypertrophy_day(db),
                        "day_6": [],
                        "day_7": get_upper_body_hypertrophy_day(db),
                        "day_8": get_lower_body_hypertrophy_day(db),
                    }
                elif meso_data["name"] == "Силовая интенсификация":
                    # 6-day cycle: U/L/R/U/L/R
                    schedule = {
                        "day_1": get_upper_body_strength_day(db),
                        "day_2": get_lower_body_strength_day(db),
                        "day_3": [],
                        "day_4": get_upper_body_strength_day(db),
                        "day_5": get_lower_body_strength_day(db),
                        "day_6": [],
                    }
                elif meso_data["name"] == "Делоад":
                    # 7-day cycle: F/R/F/R/F/R/R
                    schedule = {
                        "day_1": get_deload_day(db),
                        "day_2": [],
                        "day_3": get_deload_day(db),
                        "day_4": [],
                        "day_5": get_deload_day(db),
                        "day_6": [],
                        "day_7": [],
                    }

                micro = Microcycle(
                    name=f"Неделя {micro_idx + 1}",
                    order_index=micro_idx,
                    schedule=schedule,
                )
                meso.microcycles.append(micro)

            new_plan.mesocycles.append(meso)

        db.add(new_plan)
        db.commit()
        print(f"Successfully created training program: '{plan_name}'")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
        raise
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)  # Ensure tables are created
    parser = argparse.ArgumentParser(
        description="Seed a detailed power-building training program."
    )
    parser.add_argument(
        "--name",
        type=str,
        default="Программа 'ПРОГРЕСС ЖИМ/НОГИ'",
        help="Name for the training plan.",
    )
    parser.add_argument(
        "--no-drop",
        action="store_true",
        help="Do not delete an existing plan with the same name.",
    )
    args = parser.parse_args()

    seed_program(plan_name=args.name, drop_existing=not args.no_drop)


if __name__ == "__main__":
    main()
