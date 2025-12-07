import json
import logging
import math
import os
import time
from datetime import date, datetime, timedelta

from google import genai

from ..models import UserMax
from .exercise_service import get_all_exercises_meta
from .true_1rm_service import calculate_true_1rm

logger = logging.getLogger(__name__)


_CACHE: dict[tuple[int, int, float], tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 300


EXERCISE_MOVEMENT_SCALE = {
    "compound": 1.0,
    "isolation": 0.6,
}

EXERCISE_REGION_SCALE = {
    "lower": 1.35,
    "upper": 1.0,
}

EXERCISE_EQUIPMENT_SCALE = {
    "barbell": 1.0,
    "machine": 0.85,
    "dumbbells": 0.8,
    "cable": 0.75,
    "bodyweight": 0.85,
}


def _exercise_norm_factor(meta: dict) -> float:
    try:
        mv = str((meta or {}).get("movement_type", "")).lower()
        rg = str((meta or {}).get("region", "")).lower()
        eq = str((meta or {}).get("equipment", "")).lower()
        f = (
            EXERCISE_MOVEMENT_SCALE.get(mv, 1.0)
            * EXERCISE_REGION_SCALE.get(rg, 1.0)
            * EXERCISE_EQUIPMENT_SCALE.get(eq, 1.0)
        )

        return max(0.25, min(2.0, float(f)))
    except Exception:
        return 1.0


def _now_ts() -> float:
    return time.time()


def _exp_decay_weight(sample_date: date, half_life_days: float = 90.0) -> float:
    try:
        age_days = (datetime.utcnow().date() - sample_date).days
        if age_days <= 0:
            return 1.0
        lam = math.log(2.0) / max(1e-6, half_life_days)
        return math.exp(-lam * age_days)
    except Exception:
        return 1.0


class AlgorithmicLLMHelper:
    def __init__(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client: genai.Client | None
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to init genai client: {e}")
                self.client = None
        else:
            self.client = None

    def classify_muscle_priority(self, muscle_data: dict) -> dict:
        z = float(muscle_data.get("z") or 0.0)

        if not self.client:
            return {
                "priority": ("high" if z < -1.0 else ("low" if z > 0.5 else "medium")),
                "reason": "fallback",
            }

        prompt = (
            "Проанализируй данные мышцы и определи приоритет тренировки (high, medium, low).\n"
            f"Название: {muscle_data.get('muscle')}\n"
            f"Z-оценка: {muscle_data.get('z')}\n"
            f"Сила: {muscle_data.get('score')}\n"
            f"Тренд Δ: {muscle_data.get('trend', {}).get('delta')}\n\n"
            "Правила:\n"
            "1) z < -1.0 → high\n2) z < -0.5 и отрицательный тренд → high\n3) z > 0.5 → low\n"
            "Верни строго JSON {\"priority\": \"high|medium|low\", \"reason\": \"строка\"} без пояснений."
        )
        try:
            resp = self.client.models.generate_content(
                model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            text = getattr(resp, "text", None) or str(resp)
            data = json.loads(text)
            if isinstance(data, dict) and data.get("priority"):
                return {
                    "priority": str(data.get("priority")),
                    "reason": str(data.get("reason", "")),
                }
        except Exception as e:
            logger.warning(f"LLM classify failed, using fallback: {e}")
        return {
            "priority": ("high" if z < -1.0 else ("low" if z > 0.5 else "medium")),
            "reason": "fallback",
        }

    def classify_muscle_priorities_batch(self, muscles: list[dict]) -> list[dict]:
        if not muscles:
            return []

        if not self.client:
            return [self.classify_muscle_priority(m) for m in muscles]

        compact = [
            {
                "muscle": m.get("muscle"),
                "z": float(m.get("z") or 0.0),
                "score": float(m.get("score") or 0.0),
                "delta": (m.get("trend") or {}).get("delta"),
            }
            for m in muscles
        ]

        prompt = (
            "Проанализируй список мышц и присвой каждой приоритет тренировки (high, medium, low).\n"
            "Возвращай строго JSON массив объектов в том же порядке, что и вход, с ключами"
            ' {"priority": "high|medium|low", "reason": "строка"}.\n'
            f"Данные: {json.dumps(compact, ensure_ascii=False)}"
        )

        try:
            resp = self.client.models.generate_content(
                model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            text = getattr(resp, "text", None) or str(resp)
            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) == len(muscles):
                out: list[dict] = []
                for idx, item in enumerate(parsed):
                    if isinstance(item, dict):
                        priority = str(item.get("priority", "")).strip() or "medium"
                        reason = str(item.get("reason", "")).strip()
                        out.append({"priority": priority, "reason": reason})
                    else:
                        out.append(self.classify_muscle_priority(muscles[idx]))
                return out
        except Exception as e:
            logger.warning(f"Batch LLM classify failed, falling back: {e}")

        return [self.classify_muscle_priority(m) for m in muscles]

    def detect_anomalies(self, samples: list[dict]) -> list[int]:
        if not self.client or len(samples) < 5:
            return []
        try:
            prompt = (
                "Определи индексы аномалий в последовательности записей user_max (0-based).\n"
                "Аномалия: >3σ от соседей, резкий скачок >50% без прогрессии, против тренда.\n"
                f"Данные: {json.dumps(samples, ensure_ascii=False)}\n"
                "Верни строго JSON массив индексов, например: [0, 5]."
            )
            resp = self.client.models.generate_content(
                model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            text = getattr(resp, "text", None) or str(resp)
            data = json.loads(text)
            if isinstance(data, list):
                return [int(x) for x in data if isinstance(x, int | float)]
        except Exception as e:
            logger.warning(f"LLM anomaly detection failed: {e}")
        return []


def aggregate_exercise_strength_from_daily_agg(daily_rows) -> dict[int, float]:
    num: dict[int, float] = {}
    den: dict[int, float] = {}
    for row in daily_rows or []:
        ex_id = getattr(row, "exercise_id", None)
        dt = getattr(row, "date", None)
        sum_true_1rm = getattr(row, "sum_true_1rm", None)
        cnt = getattr(row, "cnt", None)
        if ex_id is None or dt is None:
            continue
        try:
            cnt_f = float(cnt)
            sum_f = float(sum_true_1rm)
        except (TypeError, ValueError):
            continue
        if cnt_f <= 0:
            continue
        w = _exp_decay_weight(dt)
        num[ex_id] = num.get(ex_id, 0.0) + sum_f * w
        den[ex_id] = den.get(ex_id, 0.0) + cnt_f * w

    out: dict[int, float] = {}
    for ex_id, n in num.items():
        d = den.get(ex_id, 0.0)
        if d > 0:
            out[ex_id] = n / d
    return out


def _weighted_quantile(values: list[float], weights: list[float], q: float) -> float:
    try:
        n = len(values)
        if n == 0:
            return 0.0
        if len(weights) != n:
            weights = [1.0] * n
        pairs = sorted(zip(values, weights), key=lambda x: x[0])
        vals = [v for v, _ in pairs]
        ws = [max(0.0, float(w)) for _, w in pairs]
        tot = sum(ws)
        if tot <= 0.0:
            mid = n // 2
            return vals[mid] if n % 2 == 1 else 0.5 * (vals[mid - 1] + vals[mid])
        target = max(0.0, min(1.0, q)) * tot
        csum = 0.0
        for v, w in zip(vals, ws):
            csum += w
            if csum >= target:
                return v
        return vals[-1]
    except Exception:
        try:
            s = sorted(values)
            mid = len(s) // 2
            return s[mid] if len(s) % 2 == 1 else 0.5 * (s[mid - 1] + s[mid])
        except Exception:
            return 0.0


def _weighted_median(values: list[float], weights: list[float]) -> float:
    return _weighted_quantile(values, weights, 0.5)


def _build_exercise_meta_index() -> dict[int, dict]:
    meta_list = get_all_exercises_meta()
    id_to_meta: dict[int, dict] = {}
    for m in meta_list:
        try:
            ex_id = int(m.get("id"))
            id_to_meta[ex_id] = m
        except Exception:
            continue
    return id_to_meta


def _compute_exercise_robust_stats(
    by_ex: dict[int, list[UserMax]],
    iqr_floor: float,
    sigma_floor: float,
    robust: bool = True,
    half_life_days: float = 90.0,
) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for ex_id, arr in by_ex.items():
        vals: list[float] = []
        ws: list[float] = []
        for um in arr:
            val = um.verified_1rm if getattr(um, "verified_1rm", None) else calculate_true_1rm(um)
            v = math.log1p(max(0.0, float(val)))
            w = _exp_decay_weight(getattr(um, "date", datetime.utcnow().date()), half_life_days)
            vals.append(v)
            ws.append(w)
        if not vals:
            continue
        wsum = sum(ws)
        cur_log = (sum(v * w for v, w in zip(vals, ws)) / wsum) if wsum > 0 else sum(vals) / len(vals)
        if robust:
            q1 = _weighted_quantile(vals, ws, 0.25)
            med = _weighted_quantile(vals, ws, 0.5)
            q3 = _weighted_quantile(vals, ws, 0.75)
            iqr = max((q3 - q1), float(iqr_floor))
            sigma = max(iqr / 1.349, float(sigma_floor))
        else:
            med = cur_log if wsum > 0 else (sum(vals) / len(vals))
            var = (sum(w * (v - med) ** 2 for v, w in zip(vals, ws)) / wsum) if wsum > 0 else 0.0
            sigma = max(math.sqrt(var), float(sigma_floor))
        w2 = sum(w * w for w in ws)
        n_eff = (wsum * wsum / w2) if w2 > 0 else float(len(vals))
        out[ex_id] = {"median": med, "sigma": sigma, "n_eff": n_eff, "cur_log": cur_log}
    return out


def _aggregate_muscle_scores_from_ex(
    z_by_ex: dict[int, float],
    conf_by_ex: dict[int, float],
    id_to_meta: dict[int, dict],
    synergist_weight: float,
    quantile_mode: str,
    quantile_p: float,
) -> dict[str, float]:
    mus_vals: dict[str, list[float]] = {}
    mus_ws: dict[str, list[float]] = {}
    for ex_id, z in z_by_ex.items():
        meta = id_to_meta.get(ex_id)
        if not isinstance(meta, dict):
            continue
        conf = max(0.0, float(conf_by_ex.get(ex_id, 1.0)))
        targets = meta.get("target_muscles") or []
        syner = meta.get("synergist_muscles") or []
        for m in targets:
            if isinstance(m, str):
                mus_vals.setdefault(m, []).append(z)
                mus_ws.setdefault(m, []).append(1.0 * conf)
        if synergist_weight > 0:
            for m in syner:
                if isinstance(m, str):
                    mus_vals.setdefault(m, []).append(z)
                    mus_ws.setdefault(m, []).append(float(synergist_weight) * conf)

    out: dict[str, float] = {}
    for m, vals in mus_vals.items():
        ws = mus_ws.get(m, [1.0] * len(vals))
        if not vals:
            continue
        if quantile_mode == "p":
            out[m] = _weighted_quantile(vals, ws, quantile_p)
        elif quantile_mode == "median":
            out[m] = _weighted_median(vals, ws)
        else:
            wsum = sum(ws)
            out[m] = (sum(v * w for v, w in zip(vals, ws)) / wsum) if wsum > 0 else (sum(vals) / len(vals))
    return out


def _compute_relative_trends(
    by_ex: dict[int, list[UserMax]],
    recent_days: int,
    id_to_meta: dict[int, dict],
    synergist_weight: float,
    ex_stats: dict[int, dict],
    quantile_mode: str,
    quantile_p: float,
) -> dict[str, dict]:
    today = datetime.utcnow().date()
    recent_from = today - timedelta(days=recent_days)
    prev_from = today - timedelta(days=2 * recent_days)

    rec_z_by_ex: dict[int, float] = {}
    prev_z_by_ex: dict[int, float] = {}
    rec_conf: dict[int, float] = {}
    prev_conf: dict[int, float] = {}

    for ex_id, arr in by_ex.items():
        rec_vals: list[float] = []
        prev_vals: list[float] = []
        for um in arr:
            d = getattr(um, "date", today)
            val = um.verified_1rm if getattr(um, "verified_1rm", None) else calculate_true_1rm(um)
            v = math.log1p(max(0.0, float(val)))
            if d >= recent_from:
                rec_vals.append(v)
            elif d >= prev_from:
                prev_vals.append(v)
        stats = ex_stats.get(ex_id)
        if not stats:
            continue
        sigma = float(stats.get("sigma", 0.1)) or 0.1
        med = float(stats.get("median", 0.0))
        if rec_vals:
            m = sum(rec_vals) / len(rec_vals)
            rec_z_by_ex[ex_id] = (m - med) / sigma
            rec_conf[ex_id] = math.sqrt(len(rec_vals))
        if prev_vals:
            m = sum(prev_vals) / len(prev_vals)
            prev_z_by_ex[ex_id] = (m - med) / sigma
            prev_conf[ex_id] = math.sqrt(len(prev_vals))

    rec_mus = _aggregate_muscle_scores_from_ex(
        rec_z_by_ex, rec_conf, id_to_meta, synergist_weight, quantile_mode, quantile_p
    )
    prev_mus = _aggregate_muscle_scores_from_ex(
        prev_z_by_ex, prev_conf, id_to_meta, synergist_weight, quantile_mode, quantile_p
    )

    out: dict[str, dict] = {}
    for m in set(list(rec_mus.keys()) + list(prev_mus.keys())):
        r = rec_mus.get(m)
        p = prev_mus.get(m)
        out[m] = {
            "recent_avg": r,
            "prev_avg": p,
            "delta": (None if (r is None or p is None) else (r - p)),
        }
    return out


def _aggregate_exercise_strength(user_maxes: list[UserMax]) -> dict[int, float]:
    by_ex: dict[int, list[tuple[float, float]]] = {}
    for um in user_maxes:
        val = um.verified_1rm if getattr(um, "verified_1rm", None) else calculate_true_1rm(um)
        w = _exp_decay_weight(getattr(um, "date", datetime.utcnow().date()))
        by_ex.setdefault(um.exercise_id, []).append((val, w))

    out: dict[int, float] = {}
    for ex_id, samples in by_ex.items():
        ws = sum(w for _, w in samples)
        if ws <= 0:
            continue
        out[ex_id] = sum(val * w for val, w in samples) / ws
    return out


def _distribute_to_muscles(ex_strength: dict[int, float], synergist_weight: float) -> dict[str, float]:
    logger.info(
        "distribute_to_muscles: incoming exercises=%d synergist_weight=%s",
        len(ex_strength),
        synergist_weight,
    )
    meta_list = get_all_exercises_meta()
    id_to_meta: dict[int, dict] = {}
    for m in meta_list:
        try:
            ex_id = int(m.get("id"))
            id_to_meta[ex_id] = m
        except Exception:
            continue
    logger.info("distribute_to_muscles: fetched exercise metadata=%d", len(id_to_meta))

    mus_sum: dict[str, float] = {}
    mus_wsum: dict[str, float] = {}
    missing_meta: list[int] = []
    for ex_id, strength in ex_strength.items():
        meta = id_to_meta.get(ex_id)
        if not isinstance(meta, dict):
            missing_meta.append(ex_id)
            continue

        try:
            norm_f = _exercise_norm_factor(meta)
        except Exception:
            norm_f = 1.0
        adj_strength = strength / (norm_f or 1.0)
        targets = meta.get("target_muscles") or []
        syner = meta.get("synergist_muscles") or []

        for m in targets:
            if not isinstance(m, str):
                continue
            mus_sum[m] = mus_sum.get(m, 0.0) + adj_strength * 1.0
            mus_wsum[m] = mus_wsum.get(m, 0.0) + 1.0

        if synergist_weight > 0:
            for m in syner:
                if not isinstance(m, str):
                    continue
                mus_sum[m] = mus_sum.get(m, 0.0) + adj_strength * float(synergist_weight)
                mus_wsum[m] = mus_wsum.get(m, 0.0) + float(synergist_weight)

    mus_score: dict[str, float] = {}
    for m, s in mus_sum.items():
        w = mus_wsum.get(m, 0.0)
        if w > 0:
            mus_score[m] = s / w
    if missing_meta:
        logger.warning("distribute_to_muscles: missing metadata for exercises=%s", sorted(set(missing_meta)))
    logger.info("distribute_to_muscles: output muscles=%d", len(mus_score))
    return mus_score


def _compute_trends(user_maxes: list[UserMax], recent_days: int, synergist_weight: float) -> dict[str, dict]:
    today = datetime.utcnow().date()
    recent_from = today - timedelta(days=recent_days)
    prev_from = today - timedelta(days=2 * recent_days)

    entries: dict[int, list[tuple[date, float]]] = {}
    for um in user_maxes:
        val = um.verified_1rm if getattr(um, "verified_1rm", None) else calculate_true_1rm(um)
        d = getattr(um, "date", today)
        entries.setdefault(um.exercise_id, []).append((d, val))

    meta_list = get_all_exercises_meta()
    id_to_meta: dict[int, dict] = {}
    for m in meta_list:
        try:
            ex_id = int(m.get("id"))
            id_to_meta[ex_id] = m
        except Exception:
            continue

    rec_sum: dict[str, float] = {}
    rec_w: dict[str, float] = {}
    prev_sum: dict[str, float] = {}
    prev_w: dict[str, float] = {}

    for ex_id, samples in entries.items():
        meta = id_to_meta.get(ex_id)
        if not isinstance(meta, dict):
            continue
        targets = meta.get("target_muscles") or []
        syner = meta.get("synergist_muscles") or []
        for d, val in samples:
            if d >= recent_from:
                for m in targets:
                    if isinstance(m, str):
                        rec_sum[m] = rec_sum.get(m, 0.0) + val
                        rec_w[m] = rec_w.get(m, 0.0) + 1.0
                if synergist_weight > 0:
                    for m in syner:
                        if isinstance(m, str):
                            rec_sum[m] = rec_sum.get(m, 0.0) + val * float(synergist_weight)
                            rec_w[m] = rec_w.get(m, 0.0) + float(synergist_weight)
            elif d >= prev_from:
                for m in targets:
                    if isinstance(m, str):
                        prev_sum[m] = prev_sum.get(m, 0.0) + val
                        prev_w[m] = prev_w.get(m, 0.0) + 1.0
                if synergist_weight > 0:
                    for m in syner:
                        if isinstance(m, str):
                            prev_sum[m] = prev_sum.get(m, 0.0) + val * float(synergist_weight)
                            prev_w[m] = prev_w.get(m, 0.0) + float(synergist_weight)

    out: dict[str, dict] = {}
    for m in set(list(rec_sum.keys()) + list(prev_sum.keys())):
        r_w = rec_w.get(m, 0.0)
        p_w = prev_w.get(m, 0.0)
        r = rec_sum.get(m, 0.0) / r_w if r_w > 0 else None
        p = prev_sum.get(m, 0.0) / p_w if p_w > 0 else None
        if r is not None or p is not None:
            out[m] = {
                "recent_avg": r,
                "prev_avg": p,
                "delta": (None if (r is None or p is None) else (r - p)),
            }
    return out


def compute_weak_muscles(
    user_maxes: list[UserMax],
    recent_days: int = 180,
    min_records: int = 1,
    synergist_weight: float = 0.25,
    relative_by_exercise: bool = True,
    robust: bool = True,
    quantile_mode: str = "p",
    quantile_p: float = 0.25,
    iqr_floor: float = 0.08,
    sigma_floor: float = 0.06,
    k_shrink: float = 12.0,
    z_clip: float = 3.0,
    use_llm: bool = False,
    use_cache: bool = True,
    precomputed_ex_strength: dict[int, float] | None = None,
) -> dict:
    logger.info(
        "compute_weak_muscles: received user_maxes=%d unique_exercises=%d " "recent_days=%d min_records=%d use_llm=%s",
        len(user_maxes),
        len({um.exercise_id for um in user_maxes}),
        recent_days,
        min_records,
        use_llm,
    )

    cache_key = (
        recent_days,
        min_records,
        float(synergist_weight),
        bool(use_llm),
        bool(relative_by_exercise),
        bool(robust),
        str(quantile_mode),
        float(quantile_p),
        float(iqr_floor),
        float(sigma_floor),
        float(k_shrink),
        float(z_clip),
    )
    if use_cache:
        hit = _CACHE.get(cache_key)
        if hit and (_now_ts() - hit[0] < _CACHE_TTL_SECONDS):
            logger.info("compute_weak_muscles: cache hit | key=%s", cache_key)
            return hit[1]

    if not user_maxes:
        result = {
            "recent_days": recent_days,
            "weak_muscles": [],
            "muscle_strength": {},
            "trend": {},
        }
        if use_cache:
            _CACHE[cache_key] = (_now_ts(), result)
        logger.warning("compute_weak_muscles: no user_max records found")
        return result

    by_ex: dict[int, list[UserMax]] = {}
    for um in user_maxes:
        by_ex.setdefault(um.exercise_id, []).append(um)
    if min_records > 1:
        by_ex = {k: v for k, v in by_ex.items() if len(v) >= min_records}

    filtered = [um for arr in by_ex.values() for um in arr]
    logger.info(
        "compute_weak_muscles: filtered records=%d exercises_with_records=%d",
        len(filtered),
        len(by_ex),
    )
    if not filtered:
        result = {
            "recent_days": recent_days,
            "weak_muscles": [],
            "muscle_strength": {},
            "trend": {},
        }
        if use_cache:
            _CACHE[cache_key] = (_now_ts(), result)
        logger.warning("compute_weak_muscles: filtered dataset empty after min_records filter")
        return result

    if relative_by_exercise:
        id_to_meta = _build_exercise_meta_index()

        by_ex: dict[int, list[UserMax]] = {}
        for um in filtered:
            by_ex.setdefault(um.exercise_id, []).append(um)
        ex_stats = _compute_exercise_robust_stats(
            by_ex,
            iqr_floor=iqr_floor,
            sigma_floor=sigma_floor,
            robust=robust,
        )

        z_by_ex: dict[int, float] = {}
        conf_by_ex: dict[int, float] = {}
        for ex_id, st in ex_stats.items():
            cur_log = float(st.get("cur_log", 0.0))
            med = float(st.get("median", 0.0))
            sigma = float(st.get("sigma", 0.1)) or 0.1
            n_eff = max(1e-6, float(st.get("n_eff", 1.0)))
            z_raw = (cur_log - med) / sigma
            shrink = math.sqrt(n_eff / (n_eff + float(k_shrink)))
            z = z_raw * shrink
            z = max(-float(z_clip), min(float(z_clip), z))
            z_by_ex[ex_id] = z
            conf_by_ex[ex_id] = math.sqrt(n_eff)

        muscle_strength = _aggregate_muscle_scores_from_ex(
            z_by_ex,
            conf_by_ex,
            id_to_meta,
            synergist_weight,
            quantile_mode,
            quantile_p,
        )
        trends = _compute_relative_trends(
            by_ex,
            recent_days,
            id_to_meta,
            synergist_weight,
            ex_stats,
            quantile_mode,
            quantile_p,
        )
        logger.info(
            "compute_weak_muscles: relative mode | exercises=%d muscles=%d",
            len(z_by_ex),
            len(muscle_strength),
        )

        if not muscle_strength or all(abs(v) < 0.05 for v in muscle_strength.values()):
            logger.warning(
                "compute_weak_muscles: relative mode produced empty/near-zero scores; " "falling back to absolute mode"
            )
            ex_strength = precomputed_ex_strength or _aggregate_exercise_strength(filtered)
            logger.info("compute_weak_muscles: fallback aggregated exercise strengths=%d", len(ex_strength))
            muscle_strength = _distribute_to_muscles(ex_strength, synergist_weight)
            trends = _compute_trends(filtered, recent_days, synergist_weight)
    else:
        ex_strength = precomputed_ex_strength or _aggregate_exercise_strength(filtered)
        logger.info("compute_weak_muscles: aggregated exercise strengths=%d", len(ex_strength))
        muscle_strength = _distribute_to_muscles(ex_strength, synergist_weight)
        trends = _compute_trends(filtered, recent_days, synergist_weight)
    logger.info(
        "compute_weak_muscles: muscle_strength_count=%d trend_count=%d",
        len(muscle_strength),
        len(trends),
    )

    vals = list(muscle_strength.values())
    mean = sum(vals) / len(vals) if vals else 0.0
    var = sum((v - mean) ** 2 for v in vals) / len(vals) if vals else 0.0
    std = math.sqrt(var)

    weak = []
    for m, s in muscle_strength.items():
        z = 0.0 if std == 0.0 else (s - mean) / std
        weak.append(
            {
                "muscle": m,
                "z": round(z, 3),
                "score": round(s, 2),
                "trend": trends.get(m, {}),
            }
        )
    weak.sort(key=lambda x: x["z"])

    anomalies: list[int] = []
    anomaly_details: list[dict] = []
    if use_llm:
        helper = AlgorithmicLLMHelper()
        try:
            priorities = helper.classify_muscle_priorities_batch(weak)
            for item, pr in zip(weak, priorities):
                item["priority"] = pr.get("priority", "medium")
                item["priority_reason"] = pr.get("reason", "")

            samples: list[dict] = []
            simple_samples: list[dict] = []
            for um in filtered:
                d = getattr(um, "date", datetime.utcnow().date()).isoformat()
                max_w = float(getattr(um, "max_weight", 0))
                sample: dict = {
                    "date": d,
                    "exercise_id": getattr(um, "exercise_id", None),
                    "exercise_name": getattr(um, "exercise_name", None),
                    "rep_max": getattr(um, "rep_max", None),
                    "max_weight": max_w,
                }
                v1rm = getattr(um, "verified_1rm", None)
                if v1rm is not None:
                    try:
                        sample["verified_1rm"] = float(v1rm)
                    except Exception:
                        pass
                samples.append(sample)
                simple_samples.append({"date": d, "value": max_w})
            anomalies = helper.detect_anomalies(simple_samples)
            for idx in anomalies:
                try:
                    i = int(idx)
                except (TypeError, ValueError):
                    continue
                if 0 <= i < len(samples):
                    det = dict(samples[i])
                    det["index"] = i
                    anomaly_details.append(det)
        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}")

    result = {
        "recent_days": recent_days,
        "weak_muscles": weak[:3],
        "muscle_strength": {k: round(v, 2) for k, v in muscle_strength.items()},
        "trend": trends,
        "anomalies": anomalies,
        "anomaly_details": anomaly_details,
        "llm_enabled": use_llm,
    }

    if use_cache:
        _CACHE[cache_key] = (_now_ts(), result)
    logger.info(
        "compute_weak_muscles: prepared result | weak_muscles=%d anomalies=%d",
        len(result["weak_muscles"]),
        len(anomalies),
    )
    return result
