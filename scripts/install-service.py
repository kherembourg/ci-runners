#!/usr/bin/env python3
"""Install the per-user launchd service after host qualification."""

import os
import plistlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from personal_ci.config import Config


LABEL = "dev.personal-ci.runners"


def main():
    root = ROOT
    config_path = root / "config.json"
    config = Config.load(config_path)
    credential_file = config.token_file or config.github_app.private_key_file
    if not credential_file.exists():
        raise RuntimeError("credential file is missing; service not installed")
    config.state_dir.mkdir(parents=True, exist_ok=True)
    agent_dir = Path.home() / "Library" / "LaunchAgents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    destination = agent_dir / (LABEL + ".plist")
    if destination.exists():
        raise RuntimeError("existing service file requires explicit removal before reinstall")
    payload = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, "-m", "personal_ci", "--config",
                             str(config_path), "serve"],
        "WorkingDirectory": str(root),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(config.state_dir / "controller.out.log"),
        "StandardErrorPath": str(config.state_dir / "controller.err.log"),
        "EnvironmentVariables": {"PYTHONUNBUFFERED": "1"},
    }
    with destination.open("wb") as stream:
        plistlib.dump(payload, stream)
    destination.chmod(0o644)
    domain = "gui/{}".format(os.getuid())
    subprocess.run(["launchctl", "bootstrap", domain, str(destination)], check=True)
    print("installed {} in {}".format(LABEL, domain))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print("install-service: " + str(error), file=sys.stderr)
        sys.exit(1)
