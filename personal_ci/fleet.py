"""Budgeted GitHub job admission and crash-safe VM ownership."""

import logging
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor


class Fleet:
    def __init__(self, config, github, provider, state):
        self.config = config
        self.github = github
        self.provider = provider
        self.state = state
        self.pool = ThreadPoolExecutor(max_workers=config.max_vms)
        self.futures = {}

    def _free_disk(self):
        return shutil.disk_usage(self.state.directory).free >= self.config.minimum_free_disk_gb * 1024 ** 3

    def _work(self, job, name, log_path):
        return self.provider.run_job(job, name, self.github.jit_config, log_path)

    def reap(self):
        for job_id, future in list(self.futures.items()):
            if not future.done():
                continue
            try:
                future.result()
            except Exception as error:
                logging.error("job %s ended with an infrastructure error: %s", job_id, error)
                entry = self.state.entries[str(job_id)]
                try:
                    still_exists = self.provider.exists(entry["vm"])
                except Exception:
                    still_exists = True
                if still_exists:
                    entry["phase"] = "needs_attention"
                    self.state.put(job_id, entry)
                else:
                    self.state.remove(job_id)
            else:
                self.state.remove(job_id)
            del self.futures[job_id]

    def reconcile(self):
        """Reclaim only known clones whose GitHub job is terminal."""
        for job_id, entry in list(self.state.entries.items()):
            if not job_id.isdecimal() or not isinstance(entry, dict):
                logging.error("invalid ownership ledger entry %s; leaving untouched", job_id)
                continue
            numeric_job_id = int(job_id)
            if numeric_job_id in self.futures:
                continue
            expected_prefix = "personal-ci-{}-{}-".format(entry.get("lane"), job_id)
            name = entry.get("vm", "")
            if not name.startswith(expected_prefix) or entry.get("repo") not in self.config.repositories:
                logging.error("invalid ownership ledger entry %s; leaving untouched", job_id)
                continue
            try:
                if not self.provider.exists(name):
                    self.state.remove(job_id)
                    continue
                if self.github.job_status(entry["repo"], numeric_job_id) == "completed":
                    self.provider.stop_delete(name)
                    self.state.remove(job_id)
            except Exception as error:
                logging.error("could not reconcile job %s: %s", job_id, error)

    def tick(self):
        self.reap()
        self.reconcile()
        if not self._free_disk():
            logging.warning("free disk below configured minimum; admission paused")
            return 0
        capacity = self.config.max_vms - len(self.state.entries)
        if capacity <= 0:
            return 0
        admitted = 0
        for job in self.github.queued_jobs():
            if capacity == 0:
                break
            if str(job.job_id) in self.state.entries:
                continue
            name = "personal-ci-{}-{}-{}".format(job.lane, job.job_id, uuid.uuid4().hex[:8])
            log_path = str(self.state.directory / "logs" / (name + ".log"))
            self.state.put(job.job_id, {"vm": name, "repo": job.repository,
                                        "lane": job.lane, "phase": "running", "log": log_path})
            self.futures[job.job_id] = self.pool.submit(self._work, job, name, log_path)
            capacity -= 1
            admitted += 1
        return admitted
