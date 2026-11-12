"""Gate regressions use synthetic Git repos and mocked processes, never app DBs."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_changed as gate
from scripts.test_plan_contracts import isolated_environment


class SelectionTests(unittest.TestCase):
    def test_plan_runner_overrides_application_urls_before_imports(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "must-not-use",
                "PLANS_DATABASE_URL": "must-not-use",
                "WORKOUTS_DATABASE_URL": "must-not-use",
                "SUPPLEMENTS_DATABASE_URL": "must-not-use",
            },
        ):
            env = isolated_environment("54321", "54322")
        for key in ("DATABASE_URL", "PLANS_DATABASE_URL", "WORKOUTS_DATABASE_URL", "SUPPLEMENTS_DATABASE_URL"):
            self.assertIn("127.0.0.1:54321/contract_test", env[key])
            self.assertNotIn("sqlite", env[key])
        self.assertTrue(env["SUPPLEMENTS_DATABASE_URL"].startswith("postgresql+psycopg2://"))

    def test_docs_do_not_start_services(self):
        self.assertEqual(gate.select_checks({"docs/architecture/system-map.md", "README.md"}), ([], []))
        self.assertTrue(gate.needs_specs({"docs/architecture/system-map.md"}))

    def test_combines_boundaries_once(self):
        checks, unknown = gate.select_checks({"proto/common.proto", "services/rpe-service/rpe_service/schemas.py"})
        self.assertEqual(checks, ["plan-contracts", "rpe"])
        self.assertEqual(unknown, [])

    def test_known_plan_consumer_and_spec(self):
        for p in ("gateway/gateway_app/routes/plans.py", "openspec/specs/plan-application/spec.md"):
            with self.subTest(p=p):
                self.assertEqual(gate.select_checks({p}), (["plan-contracts"], []))

    def test_unknown_runtime_and_requirements_are_not_docs(self):
        for p in ("services/agent-service/agent_service/main.py", "analytics/test.sql", "requirements.txt"):
            with self.subTest(p=p):
                self.assertEqual(gate.select_checks({p}), ([], [p]))

    def test_text_fixture_is_not_assumed_to_be_documentation(self):
        self.assertEqual(gate.select_checks({"services/rpe-service/test-input.txt"}), (["rpe"], []))

    def test_unknown_area_blocks_without_running_suite(self):
        with patch.object(gate.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "No safe check"):
                gate.run_checks({"services/agent-service/agent_service/main.py"})
            run.assert_not_called()

    def test_list_only_does_not_execute(self):
        with patch.object(gate.subprocess, "run") as run:
            gate.run_checks({"proto/common.proto"}, list_only=True)
            run.assert_not_called()

    def test_failure_stops_following_checks(self):
        with patch.object(gate.subprocess, "run", side_effect=subprocess.CalledProcessError(7, "openspec")) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                gate.run_checks({"proto/common.proto"})
            self.assertEqual(run.call_count, 1)

    def test_missing_tool_is_failure(self):
        with patch.object(gate.subprocess, "run", side_effect=FileNotFoundError("openspec")):
            self.assertEqual(gate.main(["--files", "openspec/config.yaml", "--specs-only"]), 1)

    def test_spec_hook_does_not_start_runtime_tests(self):
        with patch.object(gate.subprocess, "run") as run:
            gate.run_checks({"openspec/specs/plan-application/spec.md"}, specs_only=True)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][0], "openspec")


class GitRangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.git("config", "core.hooksPath", "/dev/null")
        self.write("README.md", "initial")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, env=self.env).decode().strip()

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "synthetic")
        return self.git("rev-parse", "HEAD")

    def test_range_includes_all_commits_and_deletions(self):
        self.write("services/rpe-service/old.py", "old")
        self.commit()
        (self.root / "README.md").unlink()
        self.write("new name.py", "new")
        tip = self.commit()
        self.assertEqual(
            gate.changed_paths(self.root, from_ref=self.base, to_ref=tip),
            {
                "README.md",
                "services/rpe-service/old.py",
                "new name.py",
            },
        )

    def test_first_push_inspects_tree(self):
        self.assertEqual(gate.changed_paths(self.root, from_ref="0" * 40, to_ref=self.base), {"README.md"})

    def test_dirty_tree_blocks_pushed_version(self):
        self.write("untracked.py", "pending")
        with self.assertRaisesRegex(ValueError, "clean checkout"):
            gate.changed_paths(self.root, from_ref=self.base, to_ref=self.base)
        self.assertEqual(gate.changed_paths(self.root, worktree=True), {"untracked.py"})

    def test_wrong_checkout_blocks(self):
        self.write("new.py", "new")
        self.commit()
        with self.assertRaisesRegex(ValueError, "differs"):
            gate.changed_paths(self.root, to_ref=self.base)

    def test_staged_deletion_is_included(self):
        self.git("rm", "README.md")
        self.assertEqual(gate.changed_paths(self.root, staged=True), {"README.md"})

    def test_parent_hook_git_environment_cannot_redirect_repo(self):
        with patch.dict(os.environ, {"GIT_DIR": "/nonexistent-hook-repo", "GIT_INDEX_FILE": "/nonexistent-index"}):
            self.assertEqual(gate.changed_paths(self.root, to_ref=self.base), {"README.md"})


if __name__ == "__main__":
    unittest.main()
