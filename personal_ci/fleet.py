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

    def tick(self):
        self.reap()
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
