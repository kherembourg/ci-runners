import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from personal_ci.config import Config
from personal_ci.fleet import Fleet
from personal_ci.github import Job
from personal_ci.state import State


class FleetTests(unittest.TestCase):
    def test_two_jobs_admitted_and_third_deferred(self):
        config = Config.load(Path(__file__).resolve().parents[1] / "config.example.json")
        with tempfile.TemporaryDirectory() as directory:
            state = State(directory)
            jobs = [Job("demo", 1, number, "linux") for number in (10, 11, 12)]
            github = Mock(queued_jobs=Mock(return_value=jobs), jit_config=Mock())
            provider = Mock()
            blocker = __import__("threading").Event()
            provider.run_job.side_effect = lambda *args: blocker.wait(5)
            fleet = Fleet(config, github, provider, state)
            with patch.object(fleet, "_free_disk", return_value=True):
                self.assertEqual(fleet.tick(), 2)
                self.assertEqual(fleet.tick(), 0)
            self.assertEqual(len(State(directory).entries), 2)
            blocker.set()
            for future in fleet.futures.values():
                future.result(timeout=5)
            fleet.reap()
            self.assertEqual(State(directory).entries, {})

    def test_restart_reserves_unknown_instance(self):
        config = Config.load(Path(__file__).resolve().parents[1] / "config.example.json")
        with tempfile.TemporaryDirectory() as directory:
            state = State(directory)
            state.put(10, {"vm": "personal-ci-linux-10", "phase": "running"})
            state.put(11, {"vm": "personal-ci-linux-11", "phase": "running"})
            github = Mock()
            fleet = Fleet(config, github, Mock(), State(directory))
            with patch.object(fleet, "_free_disk", return_value=True):
                self.assertEqual(fleet.tick(), 0)
            github.queued_jobs.assert_not_called()

    def test_failed_job_with_deleted_clone_releases_capacity(self):
        config = Config.load(Path(__file__).resolve().parents[1] / "config.example.json")
        with tempfile.TemporaryDirectory() as directory:
            state = State(directory)
            github = Mock(queued_jobs=Mock(return_value=[Job("demo", 1, 10, "linux")]))
            provider = Mock()
            provider.run_job.side_effect = RuntimeError("runner failed")
            provider.exists.return_value = False
            fleet = Fleet(config, github, provider, state)
            with patch.object(fleet, "_free_disk", return_value=True):
                self.assertEqual(fleet.tick(), 1)
            for future in fleet.futures.values():
                with self.assertRaises(RuntimeError):
                    future.result(timeout=5)
            fleet.reap()
            self.assertEqual(State(directory).entries, {})

    def test_reconcile_reclaims_only_completed_owned_clone(self):
        config = Config.load(Path(__file__).resolve().parents[1] / "config.example.json")
        with tempfile.TemporaryDirectory() as directory:
            state = State(directory)
            state.put(10, {"vm": "personal-ci-linux-10-a1", "repo": "my-web-app",
                           "lane": "linux", "phase": "running"})
            state.put(11, {"vm": "personal-ci-linux-11-b2", "repo": "my-web-app",
                           "lane": "linux", "phase": "running"})
            github = Mock()
            github.job_status.side_effect = lambda repo, job_id: "completed" if job_id == 10 else "in_progress"
            provider = Mock()
            provider.exists.return_value = True
            fleet = Fleet(config, github, provider, State(directory))
            fleet.reconcile()
            provider.stop_delete.assert_called_once_with("personal-ci-linux-10-a1")
            self.assertEqual(set(State(directory).entries), {"11"})

    def test_reconcile_leaves_unowned_name_untouched(self):
        config = Config.load(Path(__file__).resolve().parents[1] / "config.example.json")
        with tempfile.TemporaryDirectory() as directory:
            state = State(directory)
            state.put(10, {"vm": "another-vm", "repo": "my-web-app", "lane": "linux"})
            provider = Mock()
            fleet = Fleet(config, Mock(), provider, State(directory))
            fleet.reconcile()
            provider.exists.assert_not_called()
            self.assertIn("10", State(directory).entries)


if __name__ == "__main__":
    unittest.main()
