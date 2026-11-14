#!/usr/bin/env python3
"""Run the exercises-service suite with temporary protobuf stubs and in-memory SQLite."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def isolated_environment(generated: str) -> dict[str, str]:
    """Build an isolated environment overriding .env database and Redis settings."""
    env = dict(
        os.environ,
        PYTHONPATH=generated,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        EXERCISES_DATABASE_URL="sqlite+aiosqlite:///:memory:",
        EXERCISES_REDIS_HOST="127.0.0.1",
        EXERCISES_REDIS_PORT="0",
        EXERCISES_REDIS_PASSWORD="",
    )
    return env


def main() -> None:
    """Generate temporary protobuf stubs and run exercises-service unit tests."""
    with tempfile.TemporaryDirectory(prefix="workout-exercises-proto-") as generated:
        subprocess.run(
            [
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
            ],
            cwd=ROOT,
            check=True,
        )
        env = isolated_environment(generated)
        subprocess.run(
            [
                "uv",
                "run",
                "--no-sync",
                "pytest",
                "services/exercises-service/tests/test_exercises_service.py",
                "-q",
                "--tb=short",
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"Exercises checks failed: {exc}", file=sys.stderr)
        sys.exit(exc.returncode if isinstance(exc, subprocess.CalledProcessError) else 1)
