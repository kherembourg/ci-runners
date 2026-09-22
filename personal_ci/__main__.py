"""Host-side command line for the personal runner fleet."""

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

from .config import Config
from .fleet import Fleet
from .github import GitHubClient, HttpTransport, read_token
from .state import State
from .tart import TartProvider


def main(argv=None):
    parser = argparse.ArgumentParser(prog="personal-ci")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("command", choices=("doctor", "status", "once", "serve"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = Config.load(args.config)
    provider = TartProvider(config)
    if args.command == "doctor":
        installed = provider.available_images()
        expected = {lane.base_image for lane in config.lanes.values()}
        report = {
            "tart": str(config.tart_bin),
            "images_present": sorted(installed & expected),
            "images_missing": sorted(expected - installed),
            "token_file_present": config.token_file.exists(),
            "max_vms": config.max_vms,
            "cpu_per_vm": config.cpu_per_vm,
            "memory_mb_per_vm": config.memory_mb_per_vm,
        }
        print(json.dumps(report, indent=2))
        return 0 if not report["images_missing"] and report["token_file_present"] else 1
    state = State(config.state_dir)
    if args.command == "status":
        print(json.dumps(state.entries, indent=2, sort_keys=True))
        return 0
    state.acquire()
    github = GitHubClient(config.owner, config.repositories, config.lanes,
                          HttpTransport(read_token(config.token_file)))
    fleet = Fleet(config, github, provider, state)
    if args.command == "once":
        count = fleet.tick()
        print("admitted {} job(s)".format(count))
        while fleet.futures:
            time.sleep(2)
            fleet.reap()
        return 0 if all(entry.get("phase") != "needs_attention"
                        for entry in state.entries.values()) else 1
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopping:
        try:
            fleet.tick()
        except Exception as error:
            logging.error("poll failed: %s", error)
        deadline = time.monotonic() + config.poll_seconds
        while not stopping and time.monotonic() < deadline:
            time.sleep(min(1, deadline - time.monotonic()))
    # Do not terminate a busy guest. Its owned entry reserves capacity after
    # service restart until the operator has reconciled it.
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print("personal-ci: " + str(error), file=sys.stderr)
        sys.exit(1)
