import json
import logging
import math
import os
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from google import genai

from ..models import UserMax
from .exercise_service import get_all_exercises_meta
from .true_1rm_service import calculate_true_1rm

logger = logging.getLogger(__name__)

# Simple in-memory cache
_CACHE: Dict[Tuple[int, int, float], Tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 300


# Heuristic normalization scales to improve cross-muscle comparability
# We normalize raw exercise 1RM by factors derived from metadata and then apply log1p.
# This reduces the bias where lower-body compound barbell lifts dwarf upper-body isolation lifts.
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
    """Compute a normalization factor for an exercise using its metadata.

    The factor is a product of movement_type, region and equipment scales.
    Clamped to [0.25, 2.0] to avoid extreme effects.
    """
    try:
        mv = str((meta or {}).get("movement_type", "")).lower()
        rg = str((meta or {}).get("region", "")).lower()
        eq = str((meta or {}).get("equipment", "")).lower()
        f = (
            EXERCISE_MOVEMENT_SCALE.get(mv, 1.0)
            * EXERCISE_REGION_SCALE.get(rg, 1.0)
            * EXERCISE_EQUIPMENT_SCALE.get(eq, 1.0)
        )
        # Clamp to a sensible range
        return max(0.25, min(2.0, float(f)))
    except Exception:
        return 1.0


def _now_ts() -> float:
    return time.time()


def _exp_decay_weight(sample_date: date, half_life_days: float = 90.0) -> float:
    """Exponential decay by sample age (in days)."""
    try:
        age_days = (datetime.utcnow().date() - sample_date).days
        if age_days <= 0:
            return 1.0
        lam = math.log(2.0) / max(1e-6, half_life_days)
        return math.exp(-lam * age_days)
    except Exception:
        return 1.0


class AlgorithmicLLMHelper:
    """Helper to use LLM for specific sub-tasks inside algorithmic pipeline."""

    def __init__(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client: Optional[genai.Client]
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to init genai client: {e}")
                self.client = None
        else:
            self.client = None

    def classify_muscle_priority(self, muscle_data: dict) -> dict:
        """Return {priority: high|medium|low, reason: str} using LLM; fallback to simple rule."""
        z = float(muscle_data.get("z") or 0.0)
        # Fallback quick rule if LLM not available
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

    def classify_muscle_priorities_batch(self, muscles: List[dict]) -> List[dict]:
        """Batch classify priorities to minimize API calls. Returns list aligned with inputs."""
        if not muscles:
            return []

        # If no client (no key), fallback for all
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
                out: List[dict] = []
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

        # Fallback element-wise if parsing failed
        return [self.classify_muscle_priority(m) for m in muscles]

    def detect_anomalies(self, samples: List[dict]) -> List[int]:
        """Return list of indices of anomalous samples using LLM; empty on failure."""
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
                return [int(x) for x in data if isinstance(x, (int, float))]
        except Exception as e:
            logger.warning(f"LLM anomaly detection failed: {e}")
        return []


def _weighted_quantile(values: List[float], weights: List[float], q: float) -> float:
    """Compute weighted quantile for values in [0..1]. Robust to zero/empty weights.

    - Sort by value ascending and accumulate weights until reaching q * total_weight.
    - If weights sum to 0 or inputs empty, fallback to simple median.
    """
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
            # fallback to unweighted median
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
        # very defensive fallback
        try:
            s = sorted(values)
            mid = len(s) // 2
            return s[mid] if len(s) % 2 == 1 else 0.5 * (s[mid - 1] + s[mid])
        except Exception:
            return 0.0


def _weighted_median(values: List[float], weights: List[float]) -> float:
    return _weighted_quantile(values, weights, 0.5)


def _build_exercise_meta_index() -> Dict[int, dict]:
    meta_list = get_all_exercises_meta()
    id_to_meta: Dict[int, dict] = {}
    for m in meta_list:
        try:
            ex_id = int(m.get("id"))
            id_to_meta[ex_id] = m
        except Exception:
            continue
    return id_to_meta


def _compute_exercise_robust_stats(
    by_ex: Dict[int, List[UserMax]],
    iqr_floor: float,
    sigma_floor: float,
    robust: bool = True,
    half_life_days: float = 90.0,
) -> Dict[int, dict]:
    """For each exercise, compute robust stats over log1p(1RM) with exponential decay.

    Returns per exercise:
      {"median": float, "sigma": float, "n_eff": float, "cur_log": float}
    where sigma is robust (IQR/1.349) floored by sigma_floor, and cur_log is the
    weighted mean of log1p(1RM) using decay.
    """
    out: Dict[int, dict] = {}
    for ex_id, arr in by_ex.items():
        vals: List[float] = []
        ws: List[float] = []
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
            # Weighted mean/std
            med = cur_log if wsum > 0 else (sum(vals) / len(vals))
            var = (sum(w * (v - med) ** 2 for v, w in zip(vals, ws)) / wsum) if wsum > 0 else 0.0
            sigma = max(math.sqrt(var), float(sigma_floor))
        w2 = sum(w * w for w in ws)
        n_eff = (wsum * wsum / w2) if w2 > 0 else float(len(vals))
        out[ex_id] = {"median": med, "sigma": sigma, "n_eff": n_eff, "cur_log": cur_log}
    return out


def _aggregate_muscle_scores_from_ex(
    z_by_ex: Dict[int, float],
    conf_by_ex: Dict[int, float],
    id_to_meta: Dict[int, dict],
    synergist_weight: float,
    quantile_mode: str,
    quantile_p: float,
) -> Dict[str, float]:
    """Distribute exercise z-scores to muscles and aggregate per muscle with robust statistics.

    - z_by_ex: per-exercise relative z
    - conf_by_ex: confidence weights per exercise (e.g., sqrt(n_eff))
    """
    mus_vals: Dict[str, List[float]] = {}
    mus_ws: Dict[str, List[float]] = {}
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

    out: Dict[str, float] = {}
    for m, vals in mus_vals.items():
        ws = mus_ws.get(m, [1.0] * len(vals))
        if not vals:
            continue
        if quantile_mode == "p":
            out[m] = _weighted_quantile(vals, ws, quantile_p)
        elif quantile_mode == "median":
            out[m] = _weighted_median(vals, ws)
        else:
            # mean
            wsum = sum(ws)
            out[m] = (sum(v * w for v, w in zip(vals, ws)) / wsum) if wsum > 0 else (sum(vals) / len(vals))
    return out


def _compute_relative_trends(
    by_ex: Dict[int, List[UserMax]],
    recent_days: int,
    id_to_meta: Dict[int, dict],
    synergist_weight: float,
    ex_stats: Dict[int, dict],
    quantile_mode: str,
    quantile_p: float,
) -> Dict[str, dict]:
    """Compute recent vs previous averages per muscle in relative z units.

    For each exercise: compute mean log1p(1RM) in recent and previous windows, convert each
    to z using per-exercise robust stats, then aggregate to muscles with the same aggregator.
    """
    today = datetime.utcnow().date()
    recent_from = today - timedelta(days=recent_days)
    prev_from = today - timedelta(days=2 * recent_days)

    rec_z_by_ex: Dict[int, float] = {}
    prev_z_by_ex: Dict[int, float] = {}
    rec_conf: Dict[int, float] = {}
    prev_conf: Dict[int, float] = {}

    for ex_id, arr in by_ex.items():
        rec_vals: List[float] = []
        prev_vals: List[float] = []
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

    out: Dict[str, dict] = {}
    for m in set(list(rec_mus.keys()) + list(prev_mus.keys())):
        r = rec_mus.get(m)
        p = prev_mus.get(m)
        out[m] = {
            "recent_avg": r,
            "prev_avg": p,
            "delta": (None if (r is None or p is None) else (r - p)),
        }
    return out


def _aggregate_exercise_strength(user_maxes: List[UserMax]) -> Dict[int, float]:
    """Compute an effective 1RM per exercise_id using time-decayed averaging."""
    by_ex: Dict[int, List[Tuple[float, float]]] = {}
    for um in user_maxes:
        # Effective 1RM for this record
        val = um.verified_1rm if getattr(um, "verified_1rm", None) else calculate_true_1rm(um)
        w = _exp_decay_weight(getattr(um, "date", datetime.utcnow().date()))
        by_ex.setdefault(um.exercise_id, []).append((val, w))

    out: Dict[int, float] = {}
    for ex_id, samples in by_ex.items():
        ws = sum(w for _, w in samples)
        if ws <= 0:
            continue
        out[ex_id] = sum(val * w for val, w in samples) / ws
    return out


def _distribute_to_muscles(ex_strength: Dict[int, float], synergist_weight: float) -> Dict[str, float]:
    """Map exercise strengths to muscle strengths via metadata (target/synergists)."""
    logger.info(
        "distribute_to_muscles: incoming exercises=%d synergist_weight=%s",
        len(ex_strength),
        synergist_weight,
    )
    meta_list = get_all_exercises_meta()
    id_to_meta: Dict[int, dict] = {}
    for m in meta_list:
        try:
            ex_id = int(m.get("id"))
            id_to_meta[ex_id] = m
        except Exception:
            continue
    logger.info("distribute_to_muscles: fetched exercise metadata=%d", len(id_to_meta))

    mus_sum: Dict[str, float] = {}
    mus_wsum: Dict[str, float] = {}
    missing_meta: List[int] = []
    for ex_id, strength in ex_strength.items():
        meta = id_to_meta.get(ex_id)
        if not isinstance(meta, dict):
            missing_meta.append(ex_id)
            continue
        # Normalize raw exercise strength by metadata-derived factor to improve
        # cross-exercise comparability (compound vs isolation, region, equipment).
        # This prevents lower-body barbell lifts from dominating the scores.
        try:
            norm_f = _exercise_norm_factor(meta)
        except Exception:
            norm_f = 1.0
        adj_strength = strength / (norm_f or 1.0)
        targets = meta.get("target_muscles") or []
        syner = meta.get("synergist_muscles") or []
        # Target muscles: weight 1.0
        for m in targets:
            if not isinstance(m, str):
                continue
            mus_sum[m] = mus_sum.get(m, 0.0) + adj_strength * 1.0
            mus_wsum[m] = mus_wsum.get(m, 0.0) + 1.0
        # Synergists: reduced weight
        if synergist_weight > 0:
            for m in syner:
                if not isinstance(m, str):
                    continue
                mus_sum[m] = mus_sum.get(m, 0.0) + adj_strength * float(synergist_weight)
                mus_wsum[m] = mus_wsum.get(m, 0.0) + float(synergist_weight)

    mus_score: Dict[str, float] = {}
    for m, s in mus_sum.items():
        w = mus_wsum.get(m, 0.0)
        if w > 0:
            mus_score[m] = s / w
    if missing_meta:
        logger.warning("distribute_to_muscles: missing metadata for exercises=%s", sorted(set(missing_meta)))
    logger.info("distribute_to_muscles: output muscles=%d", len(mus_score))
    return mus_score


def _compute_trends(user_maxes: List[UserMax], recent_days: int, synergist_weight: float) -> Dict[str, dict]:
    """Compute recent vs previous averages per muscle."""
    # Split into two windows: [0..recent_days] and (recent_days..2*recent_days]
    today = datetime.utcnow().date()
    recent_from = today - timedelta(days=recent_days)
    prev_from = today - timedelta(days=2 * recent_days)

    # Pre-group by exercise with timestamps
    entries: Dict[int, List[Tuple[date, float]]] = {}
    for um in user_maxes:
        val = um.verified_1rm if getattr(um, "verified_1rm", None) else calculate_true_1rm(um)
        d = getattr(um, "date", today)
        entries.setdefault(um.exercise_id, []).append((d, val))

    meta_list = get_all_exercises_meta()
    id_to_meta: Dict[int, dict] = {}
    for m in meta_list:
        try:
            ex_id = int(m.get("id"))
            id_to_meta[ex_id] = m
        except Exception:
            continue

    # Accumulators
    rec_sum: Dict[str, float] = {}
    rec_w: Dict[str, float] = {}
    prev_sum: Dict[str, float] = {}
    prev_w: Dict[str, float] = {}

    for ex_id, samples in entries.items():
        meta = id_to_meta.get(ex_id)
        if not isinstance(meta, dict):
            continue
        targets = meta.get("target_muscles") or []
        syner = meta.get("synergist_muscles") or []
        for d, val in samples:
            if d >= recent_from:
                # recent window
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
                # previous window
                for m in targets:
                    if isinstance(m, str):
                        prev_sum[m] = prev_sum.get(m, 0.0) + val
                        prev_w[m] = prev_w.get(m, 0.0) + 1.0
                if synergist_weight > 0:
                    for m in syner:
                        if isinstance(m, str):
                            prev_sum[m] = prev_sum.get(m, 0.0) + val * float(synergist_weight)
                            prev_w[m] = prev_w.get(m, 0.0) + float(synergist_weight)

    out: Dict[str, dict] = {}
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
    user_maxes: List[UserMax],
    recent_days: int = 180,
    min_records: int = 1,
    synergist_weight: float = 0.25,
    # New mode: per-exercise relative normalization with robust stats
    relative_by_exercise: bool = True,
    robust: bool = True,
    quantile_mode: str = "p",  # 'p' | 'median' | 'mean'
    quantile_p: float = 0.25,
    iqr_floor: float = 0.08,
    sigma_floor: float = 0.06,
    k_shrink: float = 12.0,
    z_clip: float = 3.0,
    use_llm: bool = False,
    use_cache: bool = True,
) -> dict:
    """
    Compute weakness profile from user_max records with time decay and exercise metadata.
    Returns a dict suitable for inclusion into prompts and UI.
    """
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

    # Filter and compute
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

    # If min_records > 1, we can optionally drop exercises with too few samples
    by_ex: Dict[int, List[UserMax]] = {}
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

    # Branch: robust per-exercise relative mode vs legacy absolute mode
    if relative_by_exercise:
        id_to_meta = _build_exercise_meta_index()
        # Build per-ex robust stats
        by_ex: Dict[int, List[UserMax]] = {}
        for um in filtered:
            by_ex.setdefault(um.exercise_id, []).append(um)
        ex_stats = _compute_exercise_robust_stats(
            by_ex,
            iqr_floor=iqr_floor,
            sigma_floor=sigma_floor,
            robust=robust,
        )

        # Current per-ex z with shrinkage and clipping
        z_by_ex: Dict[int, float] = {}
        conf_by_ex: Dict[int, float] = {}
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
        # Fallback: if relative mode yields empty or near-zero strengths (e.g., single
        # sample per exercise makes z≈0), switch to absolute mode so UI doesn't show all zeros.
        # Use a small threshold (0.05) because results are later rounded to 2 decimals.
        if not muscle_strength or all(abs(v) < 0.05 for v in muscle_strength.values()):
            logger.warning(
                "compute_weak_muscles: relative mode produced empty/near-zero scores; " "falling back to absolute mode"
            )
            ex_strength = _aggregate_exercise_strength(filtered)
            logger.info("compute_weak_muscles: fallback aggregated exercise strengths=%d", len(ex_strength))
            muscle_strength = _distribute_to_muscles(ex_strength, synergist_weight)
            trends = _compute_trends(filtered, recent_days, synergist_weight)
    else:
        ex_strength = _aggregate_exercise_strength(filtered)
        logger.info("compute_weak_muscles: aggregated exercise strengths=%d", len(ex_strength))
        muscle_strength = _distribute_to_muscles(ex_strength, synergist_weight)
        trends = _compute_trends(filtered, recent_days, synergist_weight)
    logger.info(
        "compute_weak_muscles: muscle_strength_count=%d trend_count=%d",
        len(muscle_strength),
        len(trends),
    )

    # Z-score across muscles
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
    weak.sort(key=lambda x: x["z"])  # ascending: most negative first

    # LLM enrichment
    anomalies: List[int] = []
    if use_llm:
        helper = AlgorithmicLLMHelper()
        try:
            priorities = helper.classify_muscle_priorities_batch(weak)
            for item, pr in zip(weak, priorities):
                item["priority"] = pr.get("priority", "medium")
                item["priority_reason"] = pr.get("reason", "")
            # Build simple samples for anomalies
            samples = [
                {
                    "date": getattr(um, "date", datetime.utcnow().date()).isoformat(),
                    "value": float(getattr(um, "max_weight", 0)),
                }
                for um in filtered
            ]
            anomalies = helper.detect_anomalies(samples)
        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}")

    result = {
        "recent_days": recent_days,
        "weak_muscles": weak[:3],
        "muscle_strength": {k: round(v, 2) for k, v in muscle_strength.items()},
        "trend": trends,
        "anomalies": anomalies,
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
