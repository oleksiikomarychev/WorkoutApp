"""
Parser for Hevy workout export CSV files.

Reads a Hevy CSV export and converts it into structured data
compatible with the gateway WorkoutCreateWithExercises schema.

Usage:
    python scripts/hevy_parser.py workout_data.csv
    python scripts/hevy_parser.py workout_data.csv --output parsed_workouts.json
    python scripts/hevy_parser.py workout_data.csv --dry-run
"""

from __future__ import annotations

import csv
import json
import logging
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hevy Russian exercise name → exercise_list.id mapping
# ---------------------------------------------------------------------------
HEVY_EXERCISE_MAP: dict[str, int] = {
    "Жим лежа (Штанга)": 15,                                        # Barbell Bench Press
    "Жим лежа (Гантели)": 16,                                       # Dumbbell Bench Press
    "Жим сидя над головой (Штанга)": 19,                             # Overhead Press
    "Боковые подъемы (Гантель)": 21,                                 # Lateral Raises
    "Махи в наклоне (гантели)": 23,                                  # Rear Delt Fly
    "Вертикальная тяга Широчайшими (Блок)": 25,                      # Lat Pulldown
    "Вертикальный тяга (Блок)": 25,                                  # Lat Pulldown (alt name)
    "Тяга в наклоне (Штанга)": 26,                                   # Bent-Over Barbell Row
    "Горизонтальная тяга блока": 27,                                 # Seated Cable Row
    "Сгибание рук с EZ-штангой на бицепс": 30,                      # Barbell Biceps Curl
    "Разгибание рук на трицепс (блок)": 32,                         # Cable Triceps Pushdown
    "Французский жим лежа (Штанга)": 33,                             # Skull Crusher
    "Полный присед": 35,                                             # Barbell Back Squat
    "Жим ногами (Тренажёр)": 37,                                     # Leg Press
    "Гакк-приседания (Тренажёр)": 38,                                # Hack Squat
    "Румынская становая тяга (Штанга)": 39,                          # Romanian Deadlift
    "Разгибание ног (Тренажёр)": 44,                                 # Leg Extension
    "Горизонтально-изолированый жим от груди (Тренажёр)": 50,        # Machine Chest Press
    "Жим от груди (Тренажёр)": 50,                                   # Machine Chest Press
    "Бабочка (Грудная клетка )": 51,                                 # Pec Deck Fly
    "Разводка (Тренажёр)": 51,                                       # Pec Deck Fly
    "Сгибание рук на скамье Скотта (Гантель)": 55,                  # EZ-Bar Preacher Curl
    "Сгибание рук на бицепс (Блок)": 58,                            # Cable Biceps Curl
    "Отжмания на брусьях на трицепс": 64,                            # Triceps Dip
    "Подъем носков стоя (Тренажёр)": 81,                             # Standing Calf Raise
    "Standing Calf Raise (Smith)": 81,                               # Standing Calf Raise
    "Подъем на носки сидя": 82,                                      # Seated Calf Raise
    "Тяга гантели": 111,                                             # Chest-Supported Dumbbell Row
    "Присед (Тренажёр Смита)": 138,                                  # Smith Machine Squat
    "Сгибание ног лежа (Тренажёр)": 145,                             # Lying Leg Curl
    "Жим с плеч сидя (Тренажёр)": 157,                               # Machine Shoulder Press
    "Разводка задних дельт в обратном направлении (Тренажёр)": 164,  # Reverse Pec Deck Fly
}

# ---------------------------------------------------------------------------
# Hevy set_type → gateway SetType value
# ---------------------------------------------------------------------------
SET_TYPE_MAP: dict[str, str] = {
    "normal": "normal",
    "dropset": "drop",
}

# ---------------------------------------------------------------------------
# Russian month abbreviations → month number
# ---------------------------------------------------------------------------
_RU_MONTHS: dict[str, int] = {
    "янв.": 1, "янв": 1,
    "февр.": 2, "февр": 2, "фев.": 2, "фев": 2,
    "мар.": 3, "мар": 3, "марта": 3,
    "апр.": 4, "апр": 4,
    "мая": 5, "май": 5,
    "июн.": 6, "июн": 6, "июня": 6,
    "июл.": 7, "июл": 7, "июля": 7,
    "авг.": 8, "авг": 8,
    "сент.": 9, "сент": 9, "сен.": 9,
    "окт.": 10, "окт": 10,
    "нояб.": 11, "нояб": 11, "ноя.": 11,
    "дек.": 12, "дек": 12,
}

_RU_DATE_RE = re.compile(
    r"(\d{1,2})\s+([а-яА-Яa-zA-Z.]+)\s+(\d{4}),\s*(\d{1,2}):(\d{2})"
)


def parse_ru_datetime(raw: str) -> datetime | None:
    """Parse Russian-locale date like '4 мар. 2025, 13:55'."""
    raw = raw.strip()
    if not raw:
        return None
    m = _RU_DATE_RE.match(raw)
    if not m:
        logger.warning("Cannot parse date: %r", raw)
        return None
    day, month_str, year, hour, minute = m.groups()
    month_num = _RU_MONTHS.get(month_str.lower())
    if month_num is None:
        logger.warning("Unknown month token: %r in %r", month_str, raw)
        return None
    return datetime(int(year), month_num, int(day), int(hour), int(minute))


def _safe_float(val: str) -> float | None:
    if not val or not val.strip():
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _safe_int(val: str) -> int | None:
    if not val or not val.strip():
        return None
    try:
        return int(val)
    except ValueError:
        f = _safe_float(val)
        return int(f) if f is not None else None


# ---------------------------------------------------------------------------
# Core parsing
# ---------------------------------------------------------------------------

def _build_set(row: dict[str, str]) -> dict[str, Any]:
    """Convert one CSV row into a gateway-compatible ExerciseSetCreate dict."""
    hevy_type = row.get("set_type", "").strip()
    set_type = SET_TYPE_MAP.get(hevy_type, hevy_type if hevy_type else None)

    result: dict[str, Any] = {}
    if set_type:
        result["set_type"] = set_type

    weight = _safe_float(row.get("weight_kg", ""))
    if weight is not None:
        result["weight"] = weight

    reps = _safe_int(row.get("reps", ""))
    if reps is not None:
        result["reps"] = reps

    rpe = _safe_float(row.get("rpe", ""))
    if rpe is not None:
        result["rpe"] = rpe

    duration = _safe_int(row.get("duration_seconds", ""))
    if duration is not None:
        result["duration_seconds"] = duration

    distance = _safe_float(row.get("distance_km", ""))
    if distance is not None:
        result["distance_meters"] = distance * 1000

    return result


def _workout_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (row["title"], row["start_time"], row["end_time"])


def parse_hevy_csv(csv_path: str | Path) -> list[dict[str, Any]]:
    """
    Parse a Hevy CSV export into a list of dicts compatible with
    the gateway WorkoutCreateWithExercises schema.

    Returns list of:
        {
            "name": str,
            "started_at": str (ISO),
            "completed_at": str (ISO),
            "duration_seconds": int | None,
            "notes": str | None,
            "status": "completed",
            "workout_type": "manual",
            "exercise_instances": [
                {
                    "exercise_list_id": int,
                    "sets": [ { "weight": ..., "reps": ..., ... } ],
                    "notes": str | None,
                },
            ]
        }
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    workouts_ordered: OrderedDict[tuple, dict[str, Any]] = OrderedDict()
    unmapped_exercises: dict[str, int] = {}
    total_rows = 0
    skipped_rows = 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            wk = _workout_key(row)
            exercise_title = row.get("exercise_title", "").strip()

            exercise_list_id = HEVY_EXERCISE_MAP.get(exercise_title)
            if exercise_list_id is None:
                unmapped_exercises[exercise_title] = unmapped_exercises.get(exercise_title, 0) + 1
                skipped_rows += 1
                continue

            if wk not in workouts_ordered:
                started_at = parse_ru_datetime(row["start_time"])
                completed_at = parse_ru_datetime(row["end_time"])
                duration = None
                if started_at and completed_at:
                    duration = int((completed_at - started_at).total_seconds())

                workouts_ordered[wk] = {
                    "name": row["title"].strip(),
                    "started_at": started_at.isoformat() if started_at else None,
                    "completed_at": completed_at.isoformat() if completed_at else None,
                    "duration_seconds": duration,
                    "notes": row.get("description", "").strip() or None,
                    "status": "completed",
                    "workout_type": "manual",
                    "exercise_instances": OrderedDict(),
                }

            workout = workouts_ordered[wk]
            exercises: OrderedDict = workout["exercise_instances"]

            ex_key = exercise_title
            if ex_key not in exercises:
                exercise_notes = row.get("exercise_notes", "").strip() or None
                exercises[ex_key] = {
                    "exercise_list_id": exercise_list_id,
                    "sets": [],
                    "notes": exercise_notes,
                }

            exercises[ex_key]["sets"].append(_build_set(row))

    if unmapped_exercises:
        logger.warning(
            "Unmapped exercises (skipped %d rows): %s",
            skipped_rows,
            json.dumps(unmapped_exercises, ensure_ascii=False, indent=2),
        )

    results: list[dict[str, Any]] = []
    for workout in workouts_ordered.values():
        exercises_od: OrderedDict = workout["exercise_instances"]
        workout["exercise_instances"] = list(exercises_od.values())
        results.append(workout)

    logger.info(
        "Parsed %d rows → %d workouts, %d exercise instances, %d skipped rows",
        total_rows,
        len(results),
        sum(len(w["exercise_instances"]) for w in results),
        skipped_rows,
    )

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Parse Hevy workout CSV export")
    parser.add_argument("csv_file", help="Path to Hevy CSV export file")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and show summary without full output",
    )
    args = parser.parse_args()

    workouts = parse_hevy_csv(args.csv_file)

    if args.dry_run:
        print(f"\nTotal workouts: {len(workouts)}")
        print(f"Date range: {workouts[-1]['started_at']} → {workouts[0]['started_at']}")
        print("\nFirst 5 workouts:")
        for w in workouts[:5]:
            ex_count = len(w["exercise_instances"])
            set_count = sum(len(e["sets"]) for e in w["exercise_instances"])
            print(f"  {w['started_at']}  {w['name']!r:30s}  {ex_count} exercises, {set_count} sets")
        return

    output = json.dumps(workouts, ensure_ascii=False, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        logger.info("Written to %s", args.output)
    else:
        print(output)


if __name__ == "__main__":
    main()
