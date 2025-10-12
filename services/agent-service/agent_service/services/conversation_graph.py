from enum import Enum
from typing import Dict, List, Deque, Optional, Tuple, Any
from collections import deque
import httpx
import os
import logging
import time
import asyncio
import re
import json
try:
    import json5  # type: ignore
except Exception:  # pragma: no cover
    json5 = None  # type: ignore
from langchain.agents import AgentExecutor, Tool, initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from google.api_core.exceptions import ResourceExhausted
from ..config import Settings
from ..schemas.user_data import UserDataInput
from ..schemas.training_plans import TrainingPlan
from .plan_generation import generate_training_plan, generate_training_plan_with_rationale, generate_training_plan_with_summary
from ..prompts.conversation import (
    EXTRACT_USER_DATA_SYSTEM_PROMPT,
    build_state_completion_system_prompt,
    build_validation_system_prompt,
    get_state_requirements,
    get_state_system_prompt,
)



# Load settings
settings = Settings()


def _initialize_chat_llm(*, temperature: float = 0.7) -> BaseChatModel:
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable must be set")
    os.environ["GOOGLE_API_KEY"] = google_api_key
    model_name = settings.llm_model
    logging.info('Using Gemini model %s', model_name)
    return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)

# Minimal schema validation helper to avoid extra dependency
def validate(value, schema: Dict) -> bool:
    try:
        # Enum validation
        if "enum" in schema:
            return value in schema["enum"]

        # Type-based validations
        expected_type = schema.get("type")
        if expected_type == "string":
            if not isinstance(value, str):
                return False
            pattern = schema.get("pattern")
            if pattern is not None:
                return re.search(pattern, value) is not None
            return True

        if expected_type == "object":
            if not isinstance(value, dict):
                return False
            properties = schema.get("properties", {})
            for key, prop in properties.items():
                if key not in value:
                    return False
                prop_type = prop.get("type")
                if prop_type == "number" and not isinstance(value[key], (int, float)):
                    return False
            return True
    except Exception:
        return False


class ConversationState(Enum):
    COLLECT_GOALS = "collect_goals"
    COLLECT_CONSTRAINTS = "collect_constraints"
    COLLECT_PREFERENCES = "collect_preferences"
    GENERATE = "generate"

class AutonomyManager:
    """Manages autonomous question generation and state completion"""

    def __init__(self):
        # Prefer GOOGLE_API_KEY, but accept GEMINI_API_KEY as an alias
        self.llm = _initialize_chat_llm(temperature=0.7)
        # Will keep track of what data is still missing after CoT analysis
        self.last_missing_requirements: List[str] = []
        self.last_followup_question: Optional[str] = None
        self.validation_warnings: List[str] = []

        # Allowed canonical goal keys used across the pipeline
        self._EN_GOALS: List[str] = [
            "weight_loss",
            "strength",
            "endurance",  
            "muscle_definition",
            "general_fitness",
        ]

    # -----------------------------
    # Normalization helpers
    # -----------------------------

    def _canonicalize_goals(self, goals: Optional[List[str]]) -> Optional[List[str]]:
        if not goals:
            return None
        canon: List[str] = []
        for g in goals:
            if not isinstance(g, str):
                continue
            gl = g.strip().lower()
            # Simple contains-based normalization with multilingual/intent coverage
            # Weight loss
            if (
                ("weight" in gl and "loss" in gl)
                or "fat loss" in gl
                or "сброс" in gl
                or "похуд" in gl
            ):
                canon.append("weight_loss")
                continue
            # Strength (broad, including specific lift improvement intents)
            strength_markers = [
                "strength", "power", "powerlifting", "stronger", "1rm", "one-rep",
                "bench", "press", "deadlift", "squat",
                "жим", "присед", "станов", "тяга", "сил", "увелич", "повысить",
            ]
            if any(m in gl for m in strength_markers):
                canon.append("strength")
                continue
            # Endurance
            if (
                "endurance" in gl or "cardio" in gl or "run" in gl or
                "вынослив" in gl or "кардио" in gl or "бег" in gl
            ):
                canon.append("endurance")
                continue
            # Muscle definition / hypertrophy
            if (
                "muscle" in gl or "definition" in gl or "hypertrophy" in gl or
                "гипертроф" in gl or "масса" in gl or "мышц" in gl or "набор" in gl
            ):
                canon.append("muscle_definition")
                continue
            # Direct canonical values if already correct
            if gl in self._EN_GOALS:
                canon.append(gl)
        # Deduplicate and keep only allowed keys
        canon = [c for c in dict.fromkeys(canon) if c in self._EN_GOALS]
        return canon or None

    

    def _merge_lists(self, a: List[str] | None, b: List[str] | None) -> List[str]:
        out: List[str] = []
        for lst in (a or []), (b or []):
            for v in lst:
                if isinstance(v, str):
                    vv = v.strip()
                    if vv and vv not in out:
                        out.append(vv)
        return out

    def _loads_relaxed(self, text: str) -> Dict:
        """Parse dict from possibly noisy LLM output.
        Strategy:
        1) json.loads
        2) fenced block ```json ... ```
        3) first balanced {...} substring
        4) json5 if available
        Returns {} if nothing works.
        """
        def attempt(payload: str) -> Optional[Dict]:
            try:
                obj = json.loads(payload)
                return obj if isinstance(obj, dict) else None
            except Exception:
                if json5 is not None:
                    try:
                        obj = json5.loads(payload)
                        return obj if isinstance(obj, dict) else None
                    except Exception:
                        return None
                return None

        # 1) direct
        parsed = attempt(text)
        if isinstance(parsed, dict):
            return parsed

        # 2) code fence
        m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
        if m:
            parsed = attempt(m.group(1))
            if isinstance(parsed, dict):
                return parsed

        # 3) first balanced object
        start = text.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                ch = text[i]
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        parsed = attempt(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                        break
        return {}

    def extract_user_data(self, user_text: str) -> Dict:
        """Extract structured fitness data.
        1) Use LLM JSON extraction (EN keys).
        2) Always include original user text in 'notes'.
        """
        prompt = [
            SystemMessage(content=EXTRACT_USER_DATA_SYSTEM_PROMPT),
            HumanMessage(content=user_text)
        ]
        extracted: Dict = {}
        try:
            resp = self.llm.invoke(prompt)
            content = resp.content if isinstance(resp.content, str) else str(resp.content)
            extracted = self._loads_relaxed(content)
            if not isinstance(extracted, dict):
                extracted = {}
        except Exception:
            extracted = {}

        merged: Dict = dict(extracted)

        # goals
        canonical_goals = self._canonicalize_goals(merged.get("goals"))
        if canonical_goals is not None:
            merged["goals"] = canonical_goals
        else:
            merged.pop("goals", None)

        # notes: always include original user text
        notes_prev = str(merged.get("notes") or "").strip()
        if user_text and user_text not in notes_prev:
            merged["notes"] = (notes_prev + (" | " if notes_prev else "") + user_text).strip()

        return merged

    def generate_question(self, state: ConversationState, context: List[str], collected_data: Dict) -> str:
        state_key = state.value
        missing_items = self.last_missing_requirements or get_state_requirements(state_key)

        prompt = [
            SystemMessage(content=get_state_system_prompt(state_key)),
            HumanMessage(content=(
                f"История диалога:\n{'\n'.join(context[-5:])}\n\n"
                f"Уже собрано: {', '.join(f'{k}: {v}' for k, v in collected_data.items()) or '-'}\n\n"
                f"Сгенерируй один персонализированный вопрос, который поможет уточнить: "
                f"{', '.join(missing_items)}. "
                "Вопрос должен заканчиваться знаком вопроса."
            ))
        ]
        try:
            response = self.llm.invoke(prompt)
        except ResourceExhausted:
            logging.warning("Gemini quota exceeded in generate_question; falling back to default question")
            return "Ошибка апи ключа"
        except Exception as e:
            logging.exception("LLM error in generate_question: %s", e)
            return "ллм не может сгенерировать вопрос"
        
        # Validate and normalize question text
        content = response.content.strip()
        if not content:
            return "Не могли бы уточнить ваши цели?"
        # Ensure the reply looks like a вопрос. Если нет знака вопроса в конце — добавим.
        if content[-1] not in "?？":
            content = content.rstrip(" .!…") + "?"
        return content
  
    def is_state_complete(self, state: ConversationState, context: List[str]) -> bool:
        state_key = state.value
        requirements_list = get_state_requirements(state_key)
        requirements = ', '.join(requirements_list)
        cot_prompt = [
            SystemMessage(content=build_state_completion_system_prompt(state_key, requirements)),
            HumanMessage(content=f"Полный контекст диалога:\n{' '.join(context)}")
        ]
        try:
            resp = self.llm.invoke(cot_prompt)
            complete, missing, followup = self._parse_cot_verdict(resp.content)
            self.last_missing_requirements = missing
            self.last_followup_question = followup
            return complete
        except ResourceExhausted:
            logging.warning("Gemini quota exceeded in is_state_complete; assuming state incomplete")
            return False
        except Exception as e:
            logging.exception("LLM error in is_state_complete (CoT): %s", e)
            return False

    # Helper to interpret CoT output
    def _parse_cot_verdict(self, text: str) -> Tuple[bool, List[str], Optional[str]]:
        """Parse CoT reply, return (is_complete, missing_requirements, followup_question)."""
        verdict_match = re.search(r"VERDICT:\s*(COMPLETE|INCOMPLETE)", text, re.I)
        missing_match = re.search(r"MISSING:\s*(.+)", text, re.I)
        question_match = re.search(r"NEXT_QUESTION:\s*(.+)", text, re.I)

        is_complete = bool(verdict_match and verdict_match.group(1).lower() == "complete")
        missing: List[str] = []
        if missing_match:
            raw = missing_match.group(1).strip()
            if raw and raw.lower() not in {"-", "none"}:
                missing = [s.strip() for s in re.split(r"[;,]", raw) if s.strip()]
        followup = None
        if question_match:
            followup_raw = question_match.group(1).strip()
            if followup_raw:
                followup = followup_raw
        return is_complete, missing, followup

    def validate_user_data(self, collected_data: Dict) -> Tuple[bool, List[str]]:
        """Validate collected user data for conflicts and realistic constraints.
        Returns (is_valid, list_of_warnings)."""
        if not collected_data:
            return True, []

        validation_prompt = [
            SystemMessage(content=build_validation_system_prompt()),
            HumanMessage(content=(
                f"Данные пользователя:\n"
                f"Цели: {collected_data.get('goals', [])}\n"
                f"Тренировок в неделю: {collected_data.get('workouts_per_microcycle', 'не указано')}\n"
                f"Оборудование: {collected_data.get('available_equipment', [])}\n"
                f"Ограничения: {collected_data.get('limits', {})}\n"
                f"Текущие показатели: {collected_data.get('current_metrics', {})}\n"
                f"Целевые показатели: {collected_data.get('target_metrics', {})}\n"
                f"Заметки: {collected_data.get('notes', '-')}"
            ))
        ]

        try:
            resp = self.llm.invoke(validation_prompt)
            return self._parse_validation_result(resp.content)
        except ResourceExhausted:
            logging.warning("Gemini quota exceeded in validate_user_data; skipping validation")
            return True, []
        except Exception as e:
            logging.exception("LLM error in validate_user_data: %s", e)
            return True, []

    def _parse_validation_result(self, text: str) -> Tuple[bool, List[str]]:
        """Parse validation response from LLM."""
        valid_match = re.search(r"VALID:\s*(YES|NO)", text, re.I)
        warnings_match = re.search(r"WARNINGS:\s*(.+?)(?=\nSEVERITY:|$)", text, re.I | re.DOTALL)
        severity_match = re.search(r"SEVERITY:\s*(LOW|MEDIUM|HIGH)", text, re.I)

        is_valid = not (valid_match and valid_match.group(1).upper() == "NO")
        warnings: List[str] = []

        if warnings_match:
            raw = warnings_match.group(1).strip()
            if raw and raw.lower() not in {"-", "none"}:
                warnings = [w.strip() for w in re.split(r"[;\n]", raw) if w.strip() and w.strip() not in {"-", "none"}]

        # Add severity prefix to warnings if HIGH
        if severity_match and severity_match.group(1).upper() == "HIGH" and warnings:
            warnings = [f"⚠️ ВАЖНО: {w}" for w in warnings]

        return is_valid, warnings

class ConversationGraph:
    """Hybrid conversation manager with state-based autonomy"""
    STATE_FLOW = [
        ConversationState.COLLECT_GOALS,
        ConversationState.COLLECT_CONSTRAINTS,
        ConversationState.COLLECT_PREFERENCES,
        ConversationState.GENERATE
    ]
    async def _build_user_input(self) -> UserDataInput:
        goals = self.collected_data.get("goals")
        # Do not inject defaults for cycles/frequency; let LLM choose if not provided by user
        workouts_per_microcycle = self.collected_data.get("workouts_per_microcycle")
        microcycles_per_mesocycle = self.collected_data.get("microcycles_per_mesocycle")
        mesocycles_per_plan = self.collected_data.get("mesocycles_per_plan")

        # Equipment: if the user didn't specify, allow all common categories instead of forcing bodyweight only
        equipment = self.collected_data.get("available_equipment")
        if not isinstance(equipment, list) or not equipment:
            equipment = ["barbell", "dumbbells", "machine", "cable", "bodyweight"]

        return UserDataInput(
            goals=goals,
            available_equipment=equipment,
            workouts_per_microcycle=workouts_per_microcycle,
            microcycles_per_mesocycle=microcycles_per_mesocycle,
            mesocycles_per_plan=mesocycles_per_plan,
            plan_duration_weeks=self.collected_data.get("plan_duration_weeks"),
            limits=self.collected_data.get("limits"),
            notes=self.collected_data.get("notes"),
            current_metrics=self.collected_data.get("current_metrics"),
            target_metrics=self.collected_data.get("target_metrics"),
            normalization_unit=self.collected_data.get("normalization_unit"),
            normalization_value=self.collected_data.get("normalization_value")
        )

    async def _save_plan(self, plan: TrainingPlan) -> str:
        # Build payload according to plans-service CalendarPlanCreate schema
        # See: services/plans-service/plans_service/schemas/calendar_plan.py
        # - root: { name, duration_weeks, mesocycles }
        # - mesocycles: { name, order_index, duration_weeks, microcycles }
        # - microcycles: { name, order_index, days_count, plan_workouts }
        # - plan_workouts: { day_label, order_index, exercises }
        # - exercises: { exercise_definition_id, sets }
        # - sets: { intensity, effort, volume }

        # Index helpers for quick lookups
        microcycles_by_meso = {}
        for mc in plan.microcycles:
            microcycles_by_meso.setdefault(mc.mesocycle_id, []).append(mc)

        workouts_by_micro = {}
        for w in plan.workouts:
            workouts_by_micro.setdefault(w.microcycle_id, []).append(w)

        exercises_by_workout = {}
        for ex in plan.exercises:
            exercises_by_workout.setdefault(ex.plan_workout_id, []).append(ex)

        sets_by_exercise = {}
        for s in plan.sets:
            sets_by_exercise.setdefault(s.plan_exercise_id, []).append(s)

        mesocycles_payload = []
        for m in plan.mesocycles:
            microcycles_payload = []
            for mc in microcycles_by_meso.get(m.id, []):
                workouts_payload = []
                for w in workouts_by_micro.get(mc.id, []):
                    exercises_payload = []
                    for ex in exercises_by_workout.get(w.id, []):
                        sets_payload = []
                        for s in sets_by_exercise.get(ex.id, []):
                            sets_payload.append({
                                "intensity": s.intensity,
                                "effort": s.effort,
                                "volume": s.volume,
                            })
                        exercises_payload.append({
                            "exercise_definition_id": ex.exercise_definition_id,
                            "sets": sets_payload,
                        })
                    workouts_payload.append({
                        "day_label": w.day_label,
                        "order_index": w.order_index,
                        "exercises": exercises_payload,
                    })
                microcycles_payload.append({
                    "name": mc.name,
                    "order_index": mc.order_index,
                    "days_count": mc.days_count,
                    "plan_workouts": workouts_payload,
                })
            mesocycles_payload.append({
                "name": m.name,
                "order_index": m.order_index,
                "duration_weeks": m.weeks_count,
                "microcycles": microcycles_payload,
            })

        plan_data = {
            "name": plan.calendar_plan.name,
            "duration_weeks": plan.calendar_plan.duration_weeks,
            "mesocycles": mesocycles_payload,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{settings.plans_service_url}/plans/calendar-plans/",
                    json=plan_data,
                    timeout=20.0,
                )
                response.raise_for_status()
                plan_id = response.json().get("id")
                logging.info(f"Successfully saved plan with ID: {plan_id}")
                return str(plan_id)
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logging.error(f"Failed to save plan: {e}")
                # Fallback to a temporary ID if saving fails
                return f"TEMP_PLAN_{int(time.time())}"

    async def process_response(self, user_input: str) -> tuple[str, bool]:
        self.context.append(user_input)

        # Extract structured info from user reply and update collected_data
        extracted = self.autonomy.extract_user_data(user_input)
        if extracted:
            self.collected_data.update(extracted)

        current_state = self.current_state()

        # Final stage: generate plan
        if current_state == ConversationState.GENERATE:
            # Validate collected data before generating plan
            is_valid, warnings = self.autonomy.validate_user_data(self.collected_data)

            # Normalize user confirmation token
            confirm_tokens = {"continue", "продолжить", "ok", "ок", "go", "generate"}
            user_tok = user_input.lower().strip()

            # If there are warnings and user has NOT confirmed, present them and wait
            if warnings and user_tok not in confirm_tokens:
                self.autonomy.validation_warnings = warnings
                warnings_text = "\n• " + "\n• ".join(warnings)
                return (
                    f"Обнаружены следующие моменты, требующие внимания:{warnings_text}\n\n"
                    f"Хотите продолжить генерацию плана или внести изменения? "
                    f"Напишите 'continue' для генерации или опишите, что хотите изменить."
                ), False

            # If the user confirmed, or no warnings — proceed with generation
            self.autonomy.validation_warnings = []
            
            user_data = await self._build_user_input()
            try:
                # Generate plan and concise in-model summary in a single call
                plan, plan_summary = await generate_training_plan_with_summary(user_data)
            except ResourceExhausted:
                logging.warning("Gemini quota exceeded during plan generation; please try later")
                return "Извините, лимит генерации плана исчерпан. Пожалуйста, попробуйте позже.", True
            except Exception as e:
                logging.exception("Plan generation failed: %s", e)
                return "Произошла ошибка при генерации плана. Попробуйте позже.", True
            plan_id = await self._save_plan(plan)
            # Use the in-model summary from the same LLM call, if present
            summary_text = (plan_summary or "").strip() if 'plan_summary' in locals() else ""
            if summary_text:
                message = (
                    f"Ваш план тренировок готов! ID: {plan_id}\n\n"
                    f"Краткое саммари плана:\n{summary_text}"
                )
            else:
                message = f"Ваш план тренировок готов! ID: {plan_id}"
            return message, True

        # Update completion status for current state (uses CoT under the hood)
        is_complete = self.autonomy.is_state_complete(current_state, list(self.context))
        self.state_completed[current_state] = is_complete

        if is_complete:
            # Advance to the next incomplete stage; if none left → GENERATE
            if not self.next_state():
                self.state_index = len(self.STATE_FLOW) - 1
        else:
            # Roll back to the earliest incomplete stage
            for idx, st in enumerate(self.STATE_FLOW):
                if not self.state_completed[st]:
                    self.state_index = idx
                    break

        current_state = self.current_state()
        if current_state == ConversationState.GENERATE:
            return "Вся информация собрана! Проверяю корректность данных...", False

        # Ask a targeted question for the current stage
        followup = self.autonomy.last_followup_question
        if followup:
            return followup, False
        return self.autonomy.generate_question(current_state, list(self.context), self.collected_data), False


    def current_state(self) -> ConversationState:
        return self.STATE_FLOW[self.state_index]


    def __init__(self):
        self.state_index = 0
        self.context: Deque[str] = deque(maxlen=30)
        self.autonomy = AutonomyManager()
        self.collected_data = {}
        # FSM 2.0: track completion status for each conversation stage
        self.state_completed: Dict[ConversationState, bool] = {s: False for s in self.STATE_FLOW}

    def next_state(self):
        for idx in range(self.state_index + 1, len(self.STATE_FLOW)):
            if not self.state_completed[self.STATE_FLOW[idx]]:
                self.state_index = idx
                return True
        return False

# -----------------------------------------------------------------------------
# LangChain agent utilities (point 8 fix)
# -----------------------------------------------------------------------------

async def fetch_exercises(query: str) -> str:
    """Fetch exercises from exercises-service asynchronously."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.exercises_service_url}/exercises/definitions/",
                params={"search": query},
                timeout=15.0,
            )
            resp.raise_for_status()
            exercises = resp.json()
            return "\n".join(f"{ex['id']}: {ex['name']}" for ex in exercises)
    except Exception as e:
        logging.error("Error fetching exercises: %s", e)
        return f"Error fetching exercises: {e}"


async def fetch_user_max(exercise_id: str) -> str:
    """Fetch user's max performance for an exercise asynchronously."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.user_max_service_url}/user-max/by_exercise/{exercise_id}",
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return f"Max: {data.get('max_value')} kg, Date: {data.get('date')}"
    except Exception as e:
        logging.error("Error fetching user max: %s", e)
        return f"Error fetching user max: {e}"


def setup_agent() -> AgentExecutor:
    """Create a LangChain agent equipped with Gemini LLM and async tools."""
    llm = _initialize_chat_llm(temperature=0.7)

    tools = [
        Tool(
            name="ExerciseDB",
            func=lambda q: asyncio.run(fetch_exercises(q)),  # sync fallback
            coroutine=fetch_exercises,
            description="Access exercise database. Input: search query.",
        ),
        Tool(
            name="UserMaxData",
            func=lambda eid: asyncio.run(fetch_user_max(eid)),  # sync fallback
            coroutine=fetch_user_max,
            description="Access user max performance data. Input: exercise ID.",
        ),
    ]

    return initialize_agent(
        tools,
        llm,
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        verbose=False,
    )