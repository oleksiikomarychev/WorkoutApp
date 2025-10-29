from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
import logging

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None


class MacroApplier:
    """Applies preview patches to downstream services in batch.

    Strategy (safe Phase 1):
    - For Adjust_Sets:
      - add_set: append a cloned set to the exercise instance in exercises-service by PUTting the full instance with new sets list
      - remove_set: remove the set by calling DELETE set endpoint if available; otherwise PUT instance without this set
    - For Adjust_Load/Adjust_Reps:
      - Update specific set fields via exercises-service's update set endpoint if available; otherwise PUT instance with updated set

    Note: Workouts may be 'generated' and have embedded sets in workouts-service.
    For Phase 1 we operate via exercises-service instances (manual path) to avoid schema differences.
    """

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.exercises_base = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002").rstrip("/")
        self.workouts_base = os.getenv("WORKOUTS_SERVICE_URL", "http://workouts-service:8004").rstrip("/")

    async def apply(self, preview: Dict[str, Any]) -> Dict[str, Any]:
        logger = logging.getLogger(__name__)
        if not httpx:
            return {"applied": 0, "errors": ["httpx not available"], "details": []}
        patches = self._collect_patches(preview)
        logger.info("MacroApplier.apply start | user_id=%s patches_total=%d", self.user_id, len(patches))
        if not patches:
            return {"applied": 0, "errors": [], "details": []}
        # Group by workout_id and exercise_id for minimal calls
        grouped: Dict[int, Dict[int, List[Dict[str, Any]]]] = {}
        for p in patches:
            wid = int(p.get("workout_id"))
            eid = int(p.get("exercise_id")) if p.get("exercise_id") is not None else -1
            grouped.setdefault(wid, {}).setdefault(eid, []).append(p)
        applied = 0
        errors: List[str] = []
        details: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=8.0) as client:
            for wid, per_ex in grouped.items():
                # Fetch instances for this workout to obtain instance/set ids
                instances = await self._fetch_instances(client, wid)
                # Build index by exercise_id
                by_ex: Dict[int, Dict[str, Any]] = {}
                for inst in instances:
                    try:
                        exid = int(inst.get("exercise_list_id"))
                        by_ex[exid] = inst
                    except Exception:
                        continue
                for eid, actions in per_ex.items():
                    logger.info(
                        "MacroApplier.apply attempt | workout_id=%s exercise_id=%s actions=%d",
                        wid,
                        eid,
                        len(actions),
                    )
                    inst = by_ex.get(eid)
                    if not inst:
                        # No instance for this exercise in this workout, skip
                        logger.warning(
                            "MacroApplier.apply skip | workout_id=%s exercise_id=%s reason=no_instance",
                            wid,
                            eid,
                        )
                        continue
                    # Prepare updated sets list
                    sets = list(inst.get("sets") or [])
                    changed = False
                    for act in actions:
                        ch = act.get("changes") or {}
                        if ch.get("action") == "add_set":
                            tpl = ch.get("template") or {}
                            new_set = {
                                "reps": tpl.get("volume"),
                                "weight": None,
                                "rpe": tpl.get("effort"),
                                # preserve extra if needed
                                "intensity": tpl.get("intensity"),
                                "volume": tpl.get("volume"),
                                "effort": tpl.get("effort"),
                            }
                            sets.append(new_set)
                            changed = True
                        elif ch.get("action") == "remove_set":
                            sid = act.get("set_id")
                            if sid is not None:
                                sets = [s for s in sets if int(s.get("id")) != int(sid)]
                                changed = True
                        else:
                            # point update: volume/intensity/weight on a set
                            sid = act.get("set_id")
                            for i, s in enumerate(sets):
                                if sid is not None and int(s.get("id")) == int(sid):
                                    updated = dict(s)
                                    if "volume" in ch:
                                        updated["reps"] = ch["volume"]
                                        updated["volume"] = ch["volume"]
                                    if "intensity" in ch:
                                        updated["intensity"] = ch["intensity"]
                                    if "weight" in ch or "working_weight" in ch:
                                        val = ch.get("weight") if ch.get("weight") is not None else ch.get("working_weight")
                                        updated["weight"] = val
                                    sets[i] = updated
                                    changed = True
                                    break
                    if not changed:
                        logger.info(
                            "MacroApplier.apply no_changes | workout_id=%s exercise_id=%s",
                            wid,
                            eid,
                        )
                        continue
                    # PUT updated instance
                    ok = await self._put_instance(client, inst, sets)
                    if ok:
                        applied += 1
                        details.append({"workout_id": wid, "exercise_id": eid, "sets_count": len(sets)})
                        logger.info(
                            "MacroApplier.apply success | workout_id=%s exercise_id=%s sets_count=%d",
                            wid,
                            eid,
                            len(sets),
                        )
                    else:
                        errors.append(f"Failed to update instance for workout {wid} exercise {eid}")
                        logger.error(
                            "MacroApplier.apply failed | workout_id=%s exercise_id=%s",
                            wid,
                            eid,
                        )
        return {"applied": applied, "errors": errors, "details": details}

    def _collect_patches(self, preview: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in preview.get("preview", []) or []:
            for p in item.get("patches", []) or []:
                out.append(p)
        return out

    async def _fetch_instances(self, client: "httpx.AsyncClient", workout_id: int) -> List[Dict[str, Any]]:
        url = f"{self.exercises_base}/exercises/instances/workouts/{workout_id}/instances"
        headers = {"X-User-Id": self.user_id}
        try:
            res = await client.get(url, headers=headers)
            if res.status_code == 200 and isinstance(res.json(), list):
                return res.json()
        except Exception:
            return []
        return []

    async def _put_instance(self, client: "httpx.AsyncClient", inst: Dict[str, Any], sets: List[Dict[str, Any]]) -> bool:
        inst_id = inst.get("id")
        if inst_id is None:
            return False
        url = f"{self.exercises_base}/exercises/instances/{inst_id}"
        headers = {"X-User-Id": self.user_id}
        payload = dict(inst)
        payload["sets"] = sets
        try:
            res = await client.put(url, json=payload, headers=headers)
            return res.status_code in (200, 201)
        except Exception:
            return False
