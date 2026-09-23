"""Durable ownership ledger for disposable VMs."""

import fcntl
import json
import os
import tempfile
from pathlib import Path


class State:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory.chmod(0o700)
        self.path = self.directory / "instances.json"
        self.lock_path = self.directory / "controller.lock"
        self.entries = json.loads(self.path.read_text()) if self.path.exists() else {}
        if not isinstance(self.entries, dict):
            raise ValueError("invalid instance ledger")

    def acquire(self):
        self.lock = self.lock_path.open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("another personal-ci controller owns this state directory") from None

    def save(self):
        descriptor, name = tempfile.mkstemp(prefix="instances-", dir=self.directory)
        try:
            with os.fdopen(descriptor, "w") as stream:
                json.dump(self.entries, stream, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(name, 0o600)
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def put(self, job_id, entry):
        self.entries[str(job_id)] = entry
        self.save()

    def remove(self, job_id):
        self.entries.pop(str(job_id), None)
        self.save()
