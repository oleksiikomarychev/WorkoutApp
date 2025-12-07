from __future__ import annotations

from collections.abc import Sequence
from textwrap import dedent

from ..schemas.user_data import UserDataInput


def _format_list(lines: Sequence[str]) -> str:
    return "\n".join(str(line) for line in lines if line)


def build_outline_prompt(*, user_data: UserDataInput, preview: str) -> str:
    """Compose prompt for LLM outline generation stage."""
    return dedent(
        f"""
        Ты — эксперт по планированию тренировок. Сгенерируй OutlineSpec (JSON) для плана на русском языке.
        Учти цели и ограничения пользователя. Используй только допустимые поля схемы OutlineSpec.
        Не добавляй сетов, только структуру: mesocycles с microcycles (или microcycle_template) и guidelines.

        Данные пользователя:
        - goals: {user_data.goals}
        - available_equipment: {user_data.available_equipment}
        - workouts_per_microcycle: {user_data.workouts_per_microcycle}
        - microcycles_per_mesocycle: {user_data.microcycles_per_mesocycle}
        - mesocycles_per_plan: {user_data.mesocycles_per_plan}
        - plan_duration_weeks: {user_data.plan_duration_weeks}

        Доступные упражнения (образец):
        {preview}
        """
    ).strip()


def build_headers_prompt(
    *,
    user_data: UserDataInput,
    workout_lines: Sequence[str],
    preview: str,
) -> str:
    """Compose prompt for LLM headers generation stage."""
    workouts_text = _format_list(workout_lines)
    return dedent(
        f"""
        Ты — ИИ-коуч. Сформируй заголовки тренировок (список упражнений без сетов) для каждого `workout`.
        Используй только упражнения из списка `available_exercises`. Сохрани порядок дней и идентификаторов.

        Входные данные:
        Цели пользователя: {user_data.goals}
        Ограничения: {user_data.limits}
        Доступное оборудование: {user_data.available_equipment}
        Рабочие тренировки:
        {workouts_text}

        Доступные упражнения:
        {preview}

        Ответ должен содержать ТОЛЬКО валидный JSON согласно схеме.
        Используй двойные кавычки, не добавляй пояснений, комментариев, суффиксов или префиксов.
        Не добавляй trailing commas и пустые поля.
        """
    ).strip()


def build_sets_prompt(
    *,
    user_data: UserDataInput,
    workout_context: Sequence[str],
    rpe_summary: str,
) -> str:
    """Compose prompt for LLM sets generation stage."""
    context_text = _format_list(workout_context)
    summary_text = rpe_summary or "недоступно"
    return dedent(
        f"""
        Ты — ИИ-тренер. Для каждой тренировки определи параметры сетов для уже выбранных упражнений.
        Используй диапазоны из RPE-таблицы и цели пользователя. Возвращай разумные значения.

        Цели: {user_data.goals}
        Ограничения: {user_data.limits}
        Доступное оборудование: {user_data.available_equipment}
        RPE таблица (сводка):
        {summary_text}

        Заголовки тренировок:
        {context_text}

        Ответ строго по схеме JSON.
        """
    ).strip()


def build_summary_rationale_prompt(*, user_data: UserDataInput, plan_context: str) -> str:
    """Compose prompt for summary and rationale stage."""
    equipment = ", ".join(user_data.available_equipment) if user_data.available_equipment else "не указано"
    workouts_per_microcycle = user_data.workouts_per_microcycle or "не указано"
    limits = user_data.limits if user_data.limits is not None else "не указаны"
    return dedent(
        f"""
        Ты - эксперт по планированию тренировок. На основе данных пользователя и сгенерированного плана, создай:

        1. **plan_summary**: Краткое резюме плана (2-3 предложения на русском), описывающее основную структуру и цели.

        2. **plan_rationale**: Структурированное обоснование ключевых решений в плане по следующим аспектам:
           - goals_interpretation: Как интерпретированы цели пользователя
           - periodization: Обоснование выбранной периодизации и длительности мезо/микроциклов
           - frequency: Обоснование частоты тренировок и распределения по неделям
           - exercise_selection: Логика выбора упражнений (баланс жимов/тяг/ног, вариативность)
           - set_parameters: Обоснование выбора интенсивности/повторений/RPE
           - constraints_equipment: Как учтены ограничения и доступное оборудование
           - progression: Стратегия прогрессии и адаптации при нехватке времени/усталости

        **Данные пользователя:**
        - Цели: {user_data.goals or "не указаны"}
        - Ограничения: {limits}
        - Доступное оборудование: {equipment}
        - Тренировок в неделю: {workouts_per_microcycle}

        **Сгенерированный план:**
        {plan_context}

        Отвечай строго в JSON формате согласно схеме. Используй фактические данные из плана. Будь
        лаконичен, но информативен.
        """
    ).strip()
