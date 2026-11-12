#!/usr/bin/env python3
"""Run the RPE suite with temporary protobuf stubs and no application database."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="workout-rpe-proto-") as generated:
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
        env = dict(os.environ, PYTHONPATH=generated)
        env.pop("RPE_TABLE_JSON", None)
        env["RPE_TABLE_PATH"] = str(ROOT / "services/rpe-service/rpe_table.json")
        subprocess.run(
            ["uv", "run", "--no-sync", "pytest", "services/rpe-service/tests/test_rpe.py", "-q", "--tb=short"],
            cwd=ROOT,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"RPE checks failed: {exc}", file=sys.stderr)
        sys.exit(exc.returncode if isinstance(exc, subprocess.CalledProcessError) else 1)
