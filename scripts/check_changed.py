#!/usr/bin/env python3
"""Select safe local checks; never discover/import arbitrary service test suites."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    "workflow": [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-v"],
    "plan-contracts": [sys.executable, "scripts/test_plan_contracts.py"],
    "rpe": [sys.executable, "scripts/test_rpe_contracts.py"],
    "exercises": [sys.executable, "scripts/test_exercises_contracts.py"],
}
RUNTIME_ROOTS = (
    "services/",
    "gateway/",
    "libs/",
    "proto/",
    "scripts/",
    "tests/",
    "analytics/",
    "social-service/",
    "messaging-service/",
    "webhook-dispatcher/",
    "tg_bot/",
)


def git(root, *args):
    # A hook exports repository-local variables; cwd must remain authoritative,
    # including when regression tests create their own disposable repositories.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.check_output(["git", *args], cwd=root, env=env)


def paths_from(data):
    return {p.decode("utf-8", errors="surrogateescape") for p in data.split(b"\0") if p}


def changed_paths(root, *, worktree=False, staged=False, from_ref=None, to_ref=None):
    if staged:
        return paths_from(git(root, "diff", "--cached", "--name-only", "--no-renames", "-z"))
    if worktree:
        return paths_from(git(root, "diff", "HEAD", "--name-only", "--no-renames", "-z")) | paths_from(
            git(root, "ls-files", "--others", "--exclude-standard", "-z")
        )
    if not to_ref:
        raise ValueError("Push revision is missing; use --worktree for an explicit manual run.")
    head = git(root, "rev-parse", "HEAD").strip()
    target = git(root, "rev-parse", "--verify", f"{to_ref}^{{commit}}").strip()
    if head != target:
        raise ValueError("Checkout HEAD differs from pushed revision; check out the pushed commit first.")
    if git(root, "status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("Push checks require a clean checkout; commit changes or run --worktree manually.")
    if from_ref and set(from_ref) != {"0"}:
        return paths_from(git(root, "diff", "--name-only", "--no-renames", "-z", from_ref, to_ref, "--"))
    # First push with no comparable remote commit: conservatively inspect the tree.
    return paths_from(git(root, "ls-tree", "-r", "--name-only", "-z", to_ref))


def needs_specs(paths):
    return any(
        p == "AGENTS.md"
        or p.startswith(("openspec/", "docs/development/", "docs/architecture/", "docs/decisions/"))
        or p in {".pre-commit-config.yaml", "scripts/check_changed.py"}
        for p in paths
    )


def select_checks(paths):
    selected, unknown = set(), []
    for p in sorted(paths):
        if p in {".pre-commit-config.yaml", "scripts/check_changed.py"} or p.startswith("scripts/tests/"):
            selected.add("workflow")
        elif p == "scripts/test_plan_contracts.py":
            selected.add("plan-contracts")
        elif p == "scripts/test_rpe_contracts.py":
            selected.add("rpe")
        elif p == "scripts/test_exercises_contracts.py":
            selected.add("exercises")
        elif any(
            f"/specs/{cap}/" in p
            for cap in (
                "plan-application",
                "plan-schedule-changes",
                "applied-plan-mass-edit",
            )
        ):
            selected.add("plan-contracts")
        elif "/specs/change-verification/" in p or p == "openspec/config.yaml":
            selected.add("workflow")
        elif p.endswith((".md", ".rst")):
            continue
        elif p.startswith(("services/plans-service/", "services/workouts-service/")):
            selected.add("plan-contracts")
        elif p.startswith("services/exercises-service/"):
            selected.add("exercises")
        elif p.startswith("services/rpe-service/") or p == "gateway/gateway_app/routes/rpe.py":
            selected.add("rpe")
        elif p in {"gateway/gateway_app/routes/plans.py", "gateway/gateway_app/routes/workouts.py"}:
            selected.add("plan-contracts")
        elif p.startswith(("proto/", "libs/backend-common/")) or p in {
            "pyproject.toml",
            "uv.lock",
            "gateway/gateway_app/main.py",
        }:
            selected.update(("plan-contracts", "rpe"))
        elif p.startswith(RUNTIME_ROOTS) or p.startswith("docker-compose") or p.endswith("requirements.txt"):
            unknown.append(p)
    return sorted(selected), unknown


def run_checks(paths, *, specs_only=False, list_only=False, root=ROOT):
    selected, unknown = ([], []) if specs_only else select_checks(paths)
    validate = needs_specs(paths) or (not specs_only and bool(paths))
    print("OpenSpec:", "validate --all --strict --no-interactive" if validate else "not affected", flush=True)
    print("Selected checks:", ", ".join(selected) or "none (no mapped behavior changed)", flush=True)
    if unknown:
        raise ValueError(
            "No safe check configured for:\n  "
            + "\n  ".join(unknown)
            + "\nRead fixtures, add a safe check to scripts/check_changed.py and record evidence in the change."
        )
    if list_only:
        return
    if validate:
        subprocess.run(["openspec", "validate", "--all", "--strict", "--no-interactive"], cwd=root, check=True)
    for name in selected:
        print(f"Running {name}", flush=True)
        subprocess.run(COMMANDS[name], cwd=root, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--worktree", action="store_true")
    source.add_argument("--staged", action="store_true")
    source.add_argument("--pre-push", action="store_true")
    source.add_argument("--files", nargs="+", metavar="PATH")
    parser.add_argument("--specs-only", action="store_true")
    parser.add_argument("--list", action="store_true", dest="list_only")
    args = parser.parse_args(argv)
    try:
        paths = (
            set(args.files)
            if args.files
            else changed_paths(
                ROOT,
                worktree=args.worktree,
                staged=args.staged,
                from_ref=os.environ.get("PRE_COMMIT_FROM_REF"),
                to_ref=os.environ.get("PRE_COMMIT_TO_REF"),
            )
        )
        run_checks(paths, specs_only=args.specs_only, list_only=args.list_only)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return exc.returncode or 1 if isinstance(exc, subprocess.CalledProcessError) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
