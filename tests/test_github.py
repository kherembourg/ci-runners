import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from personal_ci.config import Config, Lane
from personal_ci.github import AppTokenProvider, GitHubClient, HttpTransport, Job, read_token


class GitHubTests(unittest.TestCase):
    def setUp(self):
        self.lanes = {
            "linux": Lane("personal-ci-linux-arm64", "linux-base", "/runner"),
            "macos": Lane("personal-ci-macos-arm64", "mac-base", "/runner"),
        }

    def test_filters_fork_and_untrusted_events(self):
        calls = []

        def fake(method, path, payload=None):
            calls.append((method, path, payload))
            if "/runs/" in path and "/jobs" in path:
                return {"jobs": [{"id": 9, "status": "queued", "labels": ["personal-ci-linux-arm64"]}]}
            return {"workflow_runs": [
                {"id": 1, "event": "pull_request", "head_repository": {"full_name": "attacker/fork"}},
                {"id": 2, "event": "push", "head_repository": {"full_name": "kHerembourg/demo"}},
                {"id": 3, "event": "push", "head_repository": {"full_name": "attacker/fork"}},
            ] if "status=queued" in path else []}

        jobs = GitHubClient("kHerembourg", ["demo"], self.lanes, fake).queued_jobs()
        self.assertEqual(jobs, [Job("demo", 2, 9, "linux")])
        self.assertEqual(sum("/jobs" in path for _, path, _ in calls), 1)

    def test_jit_uses_single_lane_label(self):
        seen = []

        def fake(method, path, payload=None):
            seen.append((method, path, payload))
            return {"encoded_jit_config": "encoded"}

        client = GitHubClient("kHerembourg", ["demo"], self.lanes, fake)
        self.assertEqual(client.jit_config(Job("demo", 2, 9, "macos"), "runner-9"), "encoded")
        self.assertEqual(seen[0][2], {"name": "runner-9", "runner_group_id": 1,
                                      "labels": ["personal-ci-macos-arm64"], "work_folder": "_work"})

    def test_token_requires_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text("example\n")
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                read_token(path)
            path.chmod(0o600)
            self.assertEqual(read_token(path), "example")

    def test_job_status_rejects_other_repositories(self):
        client = GitHubClient("kHerembourg", ["demo"], self.lanes, Mock())
        with self.assertRaises(ValueError):
            client.job_status("work-repo", 123)

    def test_example_config_has_exact_budget(self):
        path = Path(__file__).resolve().parents[1] / "config.example.json"
        config = Config.load(path)
        self.assertEqual((config.max_vms, config.cpu_per_vm, config.memory_mb_per_vm), (2, 4, 8192))
        data = json.loads(path.read_text())
        data["memory_mb_per_vm"] = 4096
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "bad.json"
            changed.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                Config.load(changed)

    def test_config_rejects_credential_in_checkout(self):
        path = Path(__file__).resolve().parents[1] / "config.example.json"
        data = json.loads(path.read_text())
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            del data["github_app"]
            data["token_file"] = str(Path(directory) / "token")
            config_path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "outside the repository"):
                Config.load(config_path)

    def test_config_requires_one_credential_method(self):
        path = Path(__file__).resolve().parents[1] / "config.example.json"
        data = json.loads(path.read_text())
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            data["token_file"] = "/tmp/token"
            config_path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "exactly one"):
                Config.load(config_path)

    def test_app_token_scopes_repositories_and_refreshes(self):
        calls = []
        tick = [100.0]

        def request(method, path, payload, jwt):
            calls.append((method, path, payload, jwt))
            if method == "GET":
                return {"id": 42, "account": {"login": "kHerembourg"}}
            return {"token": "short-lived-" + str(len(calls))}

        provider = AppTokenProvider("kHerembourg", ["demo", "ci-runners"], 123,
                                    "/outside/key.pem", request=request,
                                    signer=lambda message: b"signed", now=lambda: 1000,
                                    monotonic=lambda: tick[0])
        self.assertEqual(provider(), "short-lived-2")
        self.assertEqual(provider(), "short-lived-2")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][2], {"repositories": ["demo", "ci-runners"],
                                       "permissions": {"actions": "read", "administration": "write"}})
        tick[0] += 3001
        self.assertEqual(provider(), "short-lived-4")

    def test_app_rejects_other_installation_owner(self):
        provider = AppTokenProvider("kHerembourg", ["demo"], 123, "/outside/key.pem",
                                    request=lambda *args: {"id": 42, "account": {"login": "other"}},
                                    signer=lambda message: b"signed")
        with self.assertRaisesRegex(RuntimeError, "owner"):
            provider()


if __name__ == "__main__":
    unittest.main()
