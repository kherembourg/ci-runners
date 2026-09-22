# Operations

## Host setup

Use an Apple Silicon Mac with 32 GiB RAM and enough free disk for a Linux image, an Xcode image, two active clones, and a 40 GiB reserve. Keep it on AC power and prevent system sleep during CI hours. A LaunchAgent starts after the user logs in; it is not a pre-login daemon.

Install Tart from the [official release](https://github.com/openai/tart/releases) or its Homebrew tap. Record and verify the archive SHA-256 before extracting it. Set `tart_bin` in the ignored `config.json` to the actual executable inside `tart.app`.

Install [Softnet](https://github.com/openai/softnet) for guest network isolation (`brew install openai/tools/softnet`). Its binary must be found in `/opt/homebrew/bin`, owned by root, and have its SUID bit set as described by the project. This privilege lets Softnet create the VM network interface; verify its source and installation path before setting it. The controller refuses to start a job clone if Softnet is unavailable.

Create separate, stopped base images. This example uses Ubuntu ARM64 and a macOS image with Xcode; choose exact supported versions and record their source digests in a private qualification log. `tart clone` may download tens of gigabytes.

```sh
tart clone ghcr.io/cirruslabs/ubuntu:24.04 personal-ci-linux-v1
tart set personal-ci-linux-v1 --cpu 4 --memory 8192
tart run --no-graphics personal-ci-linux-v1
# In another terminal while the VM runs:
tart exec -i personal-ci-linux-v1 /bin/bash -s < scripts/bootstrap-linux.sh
tart stop personal-ci-linux-v1

tart clone ghcr.io/cirruslabs/macos-tahoe-xcode:26.5 personal-ci-macos-v1
tart set personal-ci-macos-v1 --cpu 4 --memory 8192
tart run --no-graphics personal-ci-macos-v1
# In another terminal while the VM runs:
tart exec -i personal-ci-macos-v1 /bin/bash -s < scripts/bootstrap-macos.sh
tart stop personal-ci-macos-v1
```

The Linux bootstrap installs Docker Engine and the ARM64 GitHub runner. The macOS bootstrap checks Xcode and installs the ARM64 runner. Both runner archives are pinned to SHA-256. Boot each base once after provisioning and check `nproc`/`free -m` or `sysctl -n hw.ncpu`/`sysctl -n hw.memsize`, Docker in Linux, and Xcode/Swift in macOS. Keep the prepared bases stopped. Never put a registration token in a base.

## GitHub credential

Create a dedicated GitHub App owned by your personal account. Give it **Actions: read** and **Administration: read and write** repository permissions, with no subscribed events or webhook. Install it on **only the explicitly selected personal repositories**. Generate a private key and move the downloaded PEM to the Mac host, outside this checkout:

```sh
mkdir -p ~/.config/personal-ci
chmod 700 ~/.config/personal-ci
# Move the GitHub-downloaded PEM into this directory without printing it.
chmod 600 ~/.config/personal-ci/github-app.pem
```

Set `repositories`, `github_app.app_id`, and `github_app.private_key_file` in the ignored `config.json`. The controller signs a short-lived JWT locally, requests an installation token scoped again to the configured repositories and only the two required permissions, and refreshes it in memory before expiry. Neither the PEM nor the installation token is written into a VM image or log. A fine-grained PAT remains an alternative by replacing `github_app` with `token_file`, but must be limited to the same repositories and permissions.

## Start and inspect

```sh
python3 -m unittest discover -s tests -v
python3 -m personal_ci --config config.json doctor
python3 -m personal_ci --config config.json once
python3 scripts/install-service.py
launchctl print gui/$(id -u)/dev.personal-ci.runners
python3 -m personal_ci --config config.json status
```

The service writes `controller.out.log`, `controller.err.log`, `instances.json`, and per-VM logs under `state_dir`. A stopped controller does not kill a running job. After a crash, an owned instance in the ledger reserves capacity; inspect GitHub job state, the runner log, and `tart list` before cleaning it. Only delete a clone whose name and ownership match the ledger and whose job is terminal. Remove its ledger entry after deletion. No generic cleanup command deletes unknown VMs.

`python3 -m personal_ci --config config.json reconcile` checks orphaned ledger entries against GitHub. It removes a missing clone or stops and deletes an owned clone whose job is completed. It leaves running or uncertain jobs alone; the service performs this check before admitting new work.

Job clones boot with Tart's Softnet network isolation and without clipboard or host directory shares. Verify that the selected Tart release permits GitHub egress under Softnet before enabling the service.

Use a distinct label for Linux and macOS. A queued job waits for available capacity; GitHub's documented limit for an unmatched self-hosted job is 24 hours. If the Mac sleeps or loses network, jobs may time out. Keep private repositories on the runner or use trusted-event restrictions for public repositories. Never run external PR code on this host.
