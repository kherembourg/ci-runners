"""Small GitHub REST client for trusted repository jobs and JIT runners."""

import json
import os
import stat
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


TRUSTED_EVENTS = frozenset(("push", "workflow_dispatch", "schedule"))


@dataclass(frozen=True)
class Job:
    repository: str
    run_id: int
    job_id: int
    lane: str


def read_token(path):
    path = Path(path)
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise PermissionError("GitHub token file must be owned by this user and mode 0600")
    token = path.read_text().strip()
    if not token:
        raise ValueError("GitHub token file is empty")
    return token


class HttpTransport:
    def __init__(self, token):
        self.token = token

    def __call__(self, method, path, payload=None):
        url = "https://api.github.com" + path
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, method=method, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + self.token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "personal-ci-runners",
        })
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # Never print request headers, payloads, or response bodies: JIT
            # responses contain short-lived runner credentials.
            raise RuntimeError("GitHub API {} {} returned HTTP {}".format(
                method, path.split("?")[0], error.code)) from None


class GitHubClient:
    def __init__(self, owner, repositories, lanes, transport):
        self.owner = owner
        self.repositories = tuple(repositories)
        self.lanes = lanes
        self.transport = transport

    def _pages(self, path, key):
        for page in range(1, 4):
            separator = "&" if "?" in path else "?"
            result = self.transport("GET", path + separator + "per_page=100&page=" + str(page))
            entries = result[key]
            yield from entries
            if len(entries) < 100:
                break

    def queued_jobs(self):
        found = {}
        for repository in self.repositories:
            full_name = self.owner + "/" + repository
            root = "/repos/{}/{}/actions".format(self.owner, repository)
            for status in ("queued", "in_progress"):
                runs_path = root + "/runs?status=" + status
                for run in self._pages(runs_path, "workflow_runs"):
                    if run.get("event") not in TRUSTED_EVENTS:
                        continue
                    head = run.get("head_repository") or {}
                    if head.get("full_name", "").lower() != full_name.lower():
                        continue
                    jobs_path = root + "/runs/{}/jobs?filter=latest".format(run["id"])
                    for job in self._pages(jobs_path, "jobs"):
                        if job.get("status") != "queued":
                            continue
                        labels = set(job.get("labels") or ())
                        matching = [name for name, lane in self.lanes.items() if lane.label in labels]
                        if len(matching) == 1:
                            found[job["id"]] = Job(repository, run["id"], job["id"], matching[0])
        return list(found.values())

    def jit_config(self, job, runner_name):
        label = self.lanes[job.lane].label
        path = "/repos/{}/{}/actions/runners/generate-jitconfig".format(
            self.owner, job.repository)
        result = self.transport("POST", path, {
            "name": runner_name,
            "runner_group_id": 1,
            "labels": [label],
            "work_folder": "_work",
        })
        config = result.get("encoded_jit_config")
        if not config:
            raise RuntimeError("GitHub returned no JIT runner config")
        return config

    def job_status(self, repository, job_id):
        if repository not in self.repositories:
            raise ValueError("repository is not allowed")
        path = "/repos/{}/{}/actions/jobs/{}".format(self.owner, repository, job_id)
        return self.transport("GET", path)["status"]
