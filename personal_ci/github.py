"""Small GitHub REST client for trusted repository jobs and JIT runners."""

import json
import os
import stat
import base64
import subprocess
import threading
import time
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


def _api_request(method, path, payload, token):
    url = "https://api.github.com" + path
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "personal-ci-runners",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Never print credentials or response bodies.
        raise RuntimeError("GitHub API {} {} returned HTTP {}".format(
            method, path.split("?")[0], error.code)) from None


def _base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class AppTokenProvider:
    """Refresh a repository-scoped GitHub App installation token in memory."""

    def __init__(self, owner, repositories, app_id, private_key_file,
                 request=_api_request, signer=None, now=time.time, monotonic=time.monotonic):
        self.owner = owner
        self.repositories = tuple(repositories)
        self.app_id = app_id
        self.private_key_file = Path(private_key_file)
        self.request = request
        self.signer = signer or self._sign
        self.now = now
        self.monotonic = monotonic
        self.lock = threading.Lock()
        self.token = None
        self.expires_at = 0

    def _sign(self, message):
        metadata = self.private_key_file.stat()
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
            raise PermissionError("GitHub App private key must be owned by this user and mode 0600")
        result = subprocess.run(["openssl", "dgst", "-sha256", "-sign",
                                 str(self.private_key_file), "-binary"], input=message,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if result.returncode:
            raise RuntimeError("could not sign GitHub App JWT")
        return result.stdout

    def _jwt(self):
        issued = int(self.now()) - 60
        header = _base64url(b'{"alg":"RS256","typ":"JWT"}')
        claims = _base64url(json.dumps({"iat": issued, "exp": issued + 540,
                                        "iss": str(self.app_id)}, separators=(",", ":")).encode())
        message = (header + "." + claims).encode("ascii")
        return message.decode("ascii") + "." + _base64url(self.signer(message))

    def __call__(self):
        with self.lock:
            if self.token and self.monotonic() < self.expires_at:
                return self.token
            jwt = self._jwt()
            installation = self.request("GET", "/users/{}/installation".format(self.owner), None, jwt)
            if installation.get("account", {}).get("login", "").lower() != self.owner.lower():
                raise RuntimeError("GitHub App installation owner does not match configuration")
            result = self.request("POST", "/app/installations/{}/access_tokens".format(
                installation["id"]), {
                    "repositories": list(self.repositories),
                    "permissions": {"actions": "read", "administration": "write"},
                }, jwt)
            token = result.get("token")
            if not token:
                raise RuntimeError("GitHub App returned no installation token")
            self.token = token
            self.expires_at = self.monotonic() + 3000
            return token


class HttpTransport:
    def __init__(self, credential):
        self.credential = credential

    def __call__(self, method, path, payload=None):
        token = self.credential() if callable(self.credential) else self.credential
        return _api_request(method, path, payload, token)


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
