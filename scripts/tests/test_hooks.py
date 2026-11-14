"""Exercise the real pre-commit consumer in a disposable Git repo; no push/network."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        tool_dir = Path(self.temp.name) / "bin"
        tool_dir.mkdir()
        openspec = tool_dir / "openspec"
        openspec.write_text('#!/bin/sh\nexit "${CHECK_TEST_EXIT:-0}"\n')
        openspec.chmod(0o755)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GIT_", "PRE_COMMIT_")) and key != "SKIP"
        }
        self.env["PATH"] = str(tool_dir) + os.pathsep + os.environ["PATH"]
        # Exercise exactly the repository's local entries, without fetching Ruff.
        local = (ROOT / ".pre-commit-config.yaml").read_text().split("  - repo: local\n", 1)[1]
        (self.root / ".pre-commit-config.yaml").write_text("repos:\n  - repo: local\n" + local)
        (self.root / "scripts").mkdir()
        shutil.copy(ROOT / "scripts/check_changed.py", self.root / "scripts/check_changed.py")
        (self.root / "README.md").write_text("initial")
        self.call("git", "init", "-q")
        self.call("git", "config", "user.name", "Synthetic Test")
        self.call("git", "config", "user.email", "synthetic@example.invalid")
        self.commit()
        self.base = self.call("git", "rev-parse", "HEAD").stdout.strip()
        self.call("pre-commit", "install", "--hook-type", "pre-commit", "--hook-type", "pre-push")

    def call(self, *args, check=True):
        return subprocess.run(args, cwd=self.root, env=self.env, text=True, capture_output=True, check=check)

    def commit(self):
        self.call("git", "add", ".")
        self.call("git", "commit", "-qm", "synthetic")

    def push_check(self):
        return self.call(
            "pre-commit",
            "run",
            "selected-contract-checks",
            "--hook-stage",
            "pre-push",
            "--from-ref",
            self.base,
            "--to-ref",
            "HEAD",
            check=False,
        )

    def test_installed_commit_hook_propagates_validator_failure(self):
        (self.root / "README.md").write_text("change")
        self.call("git", "add", ".")
        self.env["CHECK_TEST_EXIT"] = "23"
        result = self.call("git", "commit", "-qm", "must fail", check=False)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.call("git", "rev-parse", "HEAD").stdout.strip(), self.base)

    def test_push_range_accepts_docs_and_propagates_failure(self):
        (self.root / "README.md").write_text("change")
        self.commit()  # Installed commit hook must pass.
        result = self.push_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.env["CHECK_TEST_EXIT"] = "19"
        result = self.push_check()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_push_blocks_unmapped_runtime(self):
        path = self.root / "services/agent-service/agent_service/main.py"
        path.parent.mkdir(parents=True)
        path.write_text("# synthetic")
        self.commit()
        result = self.push_check()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No safe check configured", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
