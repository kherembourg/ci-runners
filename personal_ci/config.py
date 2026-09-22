"""Validate the public configuration and keep credentials out of it."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class Lane:
    label: str
    base_image: str
    runner_dir: str


@dataclass(frozen=True)
class GitHubApp:
    app_id: int
    private_key_file: Path


@dataclass(frozen=True)
class Config:
    owner: str
    repositories: Tuple[str, ...]
    token_file: Optional[Path]
    github_app: Optional[GitHubApp]
    state_dir: Path
    tart_bin: Path
    poll_seconds: int
    max_vms: int
    cpu_per_vm: int
    memory_mb_per_vm: int
    minimum_free_disk_gb: int
    lanes: Dict[str, Lane]

    @classmethod
    def load(cls, path):
        config_path = Path(path).resolve()
        data = json.loads(config_path.read_text())
        owner = data["owner"]
        repositories = tuple(data["repositories"])
        if not NAME.fullmatch(owner) or not repositories or len(set(repositories)) != len(repositories):
            raise ValueError("owner and unique repository names are required")
        if any(not NAME.fullmatch(repo) for repo in repositories):
            raise ValueError("invalid repository name")
        lanes = {name: Lane(**entry) for name, entry in data["lanes"].items()}
        if set(lanes) != {"linux", "macos"}:
            raise ValueError("exactly linux and macos lanes are required")
        if any(not NAME.fullmatch(lane.label) or not NAME.fullmatch(lane.base_image)
               or not lane.runner_dir.startswith("/") for lane in lanes.values()):
            raise ValueError("invalid lane configuration")
        if lanes["linux"].label == lanes["macos"].label:
            raise ValueError("lane labels must differ")
        if (data["max_vms"], data["cpu_per_vm"], data["memory_mb_per_vm"]) != (2, 4, 8192):
            raise ValueError("VM budget must be two 4-vCPU, 8192-MiB guests")
        if not 10 <= data["poll_seconds"] <= 3600:
            raise ValueError("poll_seconds must be between 10 and 3600")
        if data["minimum_free_disk_gb"] < 20:
            raise ValueError("minimum_free_disk_gb must be at least 20")
        has_token = "token_file" in data
        has_app = "github_app" in data
        if has_token == has_app:
            raise ValueError("configure exactly one GitHub credential method")
        token_file = Path(data["token_file"]).expanduser().resolve() if has_token else None
        github_app = None
        if has_app:
            app = data["github_app"]
            if not isinstance(app.get("app_id"), int) or app["app_id"] <= 0:
                raise ValueError("github_app.app_id must be a positive integer")
            github_app = GitHubApp(app["app_id"], Path(app["private_key_file"]).expanduser().resolve())
        state_dir = Path(data["state_dir"]).expanduser().resolve()
        tart_bin = Path(data["tart_bin"]).expanduser().resolve()
        credential_file = token_file or github_app.private_key_file
        if not all(path.is_absolute() for path in (credential_file, state_dir, tart_bin)):
            raise ValueError("credential, state_dir, and tart_bin must be absolute")
        if credential_file == state_dir or state_dir in credential_file.parents:
            raise ValueError("credential must be outside runtime state")
        if config_path.parent in credential_file.parents:
            raise ValueError("credential must be outside the repository checkout")
        return cls(owner, repositories, token_file, github_app, state_dir, tart_bin,
                   data["poll_seconds"], data["max_vms"], data["cpu_per_vm"],
                   data["memory_mb_per_vm"], data["minimum_free_disk_gb"], lanes)
