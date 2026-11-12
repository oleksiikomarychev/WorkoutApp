#!/usr/bin/env python3
"""Run plan contract tests against disposable local Docker infrastructure."""

import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, **kwargs)


def main():
    suffix = uuid.uuid4().hex[:10]
    pg, redis = f"workout-contract-pg-{suffix}", f"workout-contract-redis-{suffix}"
    containers = []
    try:
        for name, args in (
            (
                pg,
                [
                    "-p",
                    "127.0.0.1::5432",
                    "-e",
                    "POSTGRES_PASSWORD=contract-test",
                    "-e",
                    "POSTGRES_DB=contract_test",
                    "postgres:16-alpine",
                ],
            ),
            (redis, ["-p", "127.0.0.1::6379", "redis:7-alpine"]),
        ):
            run("docker", "run", "-d", "--rm", "--name", name, *args, stdout=subprocess.DEVNULL)
            containers.append(name)
        for name, health in ((pg, ["pg_isready", "-U", "postgres"]), (redis, ["redis-cli", "ping"])):
            deadline = time.monotonic() + 30
            while True:
                result = subprocess.run(["docker", "exec", name, *health], capture_output=True)
                if result.returncode == 0:
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError(f"Test container {name} did not become ready")
                time.sleep(0.2)
        pg_port = run("docker", "port", pg, "5432", capture_output=True).stdout.strip().rsplit(":", 1)[1]
        redis_port = run("docker", "port", redis, "6379", capture_output=True).stdout.strip().rsplit(":", 1)[1]
        env = dict(
            os.environ,
            CONTRACT_TEST_POSTGRES_URL=f"postgresql+asyncpg://postgres:contract-test@127.0.0.1:{pg_port}/contract_test",
            CONTRACT_TEST_REDIS_URL=f"redis://127.0.0.1:{redis_port}/0",
        )
        with tempfile.TemporaryDirectory(prefix="workout-contract-proto-") as generated:
            run(
                "uv",
                "run",
                "--no-sync",
                "python",
                "-m",
                "grpc_tools.protoc",
                "-I",
                "proto",
                f"--python_out={generated}",
                f"--grpc_python_out={generated}",
                *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "proto").glob("*.proto"))],
            )
            # Match Docker's generated proto imports without rewriting repository stubs.
            env["PYTHONPATH"] = generated + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            commands = [
                ["tests/integration/test_plan_operation_pipeline.py"],
                [
                    "services/plans-service/tests/test_active_plan_guard_postgres.py",
                    "services/plans-service/tests/test_apply_plan_guard.py",
                    "services/plans-service/tests/test_calendar_plan_ownership.py",
                ],
                [
                    "services/workouts-service/tests/test_applied_plan_mass_edit_contract.py",
                    "services/workouts-service/tests/test_failed_application_cleanup.py",
                    "services/workouts-service/tests/test_workouts_service.py",
                ],
            ]
            for tests in commands:
                run("uv", "run", "--no-sync", "pytest", *tests, "-q", "--tb=short", env=env)
    finally:
        for name in reversed(containers):
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
