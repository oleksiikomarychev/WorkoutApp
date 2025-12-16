from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests


def _find_repo_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "docker-compose.yml").exists() and (p / "services").exists():
            return p
    return start.parent


def _default_plans_file() -> Path:
    repo_root = _find_repo_root(Path(__file__).resolve())
    return repo_root / "services" / "calendar_plans.json"


def _load_plans(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    plans = data.get("plans")
    if not isinstance(plans, list):
        raise ValueError("Expected top-level key 'plans' to be a list")

    return plans


def _ensure_day_labels(plan: dict[str, Any]) -> None:
    mesocycles = plan.get("mesocycles")
    if not isinstance(mesocycles, list):
        return

    for meso in mesocycles:
        microcycles = (meso or {}).get("microcycles")
        if not isinstance(microcycles, list):
            continue

        for micro in microcycles:
            if not isinstance(micro, dict):
                continue

            days_count = micro.get("days_count")
            workouts = micro.get("plan_workouts")
            if not isinstance(workouts, list) or not isinstance(days_count, int) or days_count < 1:
                continue

            for i, w in enumerate(workouts):
                if not isinstance(w, dict):
                    continue
                if not w.get("day_label"):
                    w["day_label"] = f"Day {i + 1}" if i < days_count else f"Day {i + 1}"


def _build_endpoint(base_url: str, target: str) -> str:
    base = base_url.rstrip("/")
    if target == "plans-service":
        return f"{base}/plans/calendar-plans/"
    if target == "gateway":
        return f"{base}/api/v1/plans/calendar-plans"
    raise ValueError(f"Unsupported target: {target}")


def _post_with_retries(
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
    retries: int,
) -> requests.Response:
    last_exc: Exception | None = None
    attempts = max(retries, 0) + 1
    for attempt in range(attempts):
        try:
            return requests.post(endpoint, headers=headers, json=payload, timeout=timeout_seconds)
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts - 1:
                raise
            time.sleep(min(2.0**attempt, 10.0))
    raise RuntimeError(f"request failed: {last_exc}")


def _build_headers(
    user_id: str | None,
    internal_secret: str | None,
    bearer_token: str | None,
) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if user_id:
        headers["X-User-Id"] = user_id
    if internal_secret:
        headers["X-Internal-Secret"] = internal_secret
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    return headers


def _fetch_existing_plan_names(endpoint: str, headers: dict[str, str], timeout_seconds: float) -> set[str] | None:
    try:
        r = requests.get(endpoint, headers=headers, params={"roots_only": "true"}, timeout=timeout_seconds)
    except Exception:
        return None

    if r.status_code >= 400:
        return None

    try:
        payload = r.json()
    except Exception:
        return None

    if not isinstance(payload, list):
        return None

    names: set[str] = set()
    for p in payload:
        if isinstance(p, dict) and isinstance(p.get("name"), str):
            names.add(p["name"])
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default=str(_default_plans_file()))
    parser.add_argument("--target", choices=["plans-service", "gateway"], default="plans-service")
    parser.add_argument("--base-url", type=str, default=None)
    parser.add_argument("--user-id", type=str, default=None)
    parser.add_argument("--internal-secret", type=str, default=None)
    parser.add_argument("--bearer-token", type=str, default=None)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.base_url is None:
        args.base_url = "http://localhost:8005" if args.target == "plans-service" else "http://localhost:8000"

    endpoint = _build_endpoint(args.base_url, args.target)
    headers = _build_headers(args.user_id, args.internal_secret, args.bearer_token)

    if args.target == "plans-service" and not args.user_id:
        print("--user-id is required when target=plans-service", file=sys.stderr)
        return 2

    if args.target == "gateway" and not (args.bearer_token or (args.internal_secret and args.user_id)):
        print(
            "For target=gateway you must provide either --bearer-token or both --internal-secret and --user-id",
            file=sys.stderr,
        )
        return 2

    plans_file = Path(args.file).expanduser().resolve()
    plans = _load_plans(plans_file)

    existing_names: set[str] = set()
    if args.skip_existing and not args.dry_run:
        fetched = _fetch_existing_plan_names(endpoint, headers, args.timeout)
        if fetched:
            existing_names = fetched

    start = max(args.start, 0)
    end = len(plans) if args.limit is None else min(len(plans), start + max(args.limit, 0))

    ok = 0
    failed = 0
    skipped = 0

    for idx in range(start, end):
        plan = plans[idx]
        if not isinstance(plan, dict):
            failed += 1
            if args.stop_on_error:
                return 1
            continue

        name = plan.get("name")
        if isinstance(name, str) and name in existing_names:
            skipped += 1
            continue

        _ensure_day_labels(plan)

        if args.dry_run:
            ok += 1
            continue

        try:
            r = _post_with_retries(endpoint, headers, plan, args.timeout, args.retries)
        except Exception as exc:
            print(f"[{idx}] request_failed name={name!r} error={exc}", file=sys.stderr)
            failed += 1
            if args.stop_on_error:
                return 1
            continue

        if r.status_code >= 400:
            body = r.text
            if len(body) > 2000:
                body = body[:2000] + "..."
            print(f"[{idx}] create_failed status={r.status_code} name={name!r} body={body}", file=sys.stderr)
            failed += 1
            if args.stop_on_error:
                return 1
        else:
            ok += 1

        if args.delay_seconds and args.delay_seconds > 0:
            time.sleep(args.delay_seconds)

    print(f"import_finished ok={ok} failed={failed} skipped={skipped} total={end - start}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
