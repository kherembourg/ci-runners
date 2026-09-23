# Operating the personal runner

This page covers administration of the Mac. To understand how the system works before using these commands, start with the [README](../README.md) and [workflow guide](workflows.md). Unless noted otherwise, run the commands below **on the Mac that hosts the VMs**, from the directory where you cloned this repository.

## Daily checks

```sh
python3 -m personal_ci --config config.json doctor
python3 -m personal_ci --config config.json status
launchctl print gui/$(id -u)/dev.personal-ci.runners
```

- `doctor` checks that both base images and the GitHub App key file exist. It does not run a build or guarantee that an application workflow will pass.
- `status` shows the registry of reserved VMs. `{}` means no job is using a VM; it is not an error.
- `launchctl` should show `state = running`. The service starts only after a user logs in to the Mac.
- In the **Actions** tab for the relevant repository, a queued job usually means it is waiting for a free VM. At most two jobs run in parallel.

To tell a VM failure from a project-specific failure, manually run [Linux VM smoke](../.github/workflows/linux-smoke.yml) or [macOS VM smoke](../.github/workflows/macos-smoke.yml) from GitHub. These workflows check the CPU, memory, and basic tools.

## Where data lives

| Item | Location | Use |
| --- | --- | --- |
| Controller code | Your repository checkout | Git checkout containing the controller. |
| Actual configuration | `config.json` in that checkout | Repository list, images, labels, and limits; ignored by Git. |
| GitHub App private key | `~/.config/personal-ci/github-app.pem` | Kept on the host, outside the repository, with `0600` permissions. |
| State and logs | `~/Library/Application Support/personal-ci/` | `instances.json`, controller logs, and per-VM logs. |
| Tart base images | Tart on the Mac | `personal-ci-linux-v1` and `personal-ci-macos-v1`, normally stopped. |

Clones created for jobs are deleted after normal completion. If the controller stops unexpectedly, the registry reserves their slots and requires inspection before deletion. Never delete an unknown VM with a global command.

## Prepare a new host

Use an Apple Silicon Mac with enough CPU and memory for two 4-vCPU, 8-GiB guests and enough disk space for both base images and two clones. A 32-GiB host is a practical starting point. Keep at least the configured **40 GiB free** after setup. Keep the Mac powered on, connected to the network, and logged in during CI hours. The service is a LaunchAgent; it is unavailable before login.

Clone this repository, then create your local configuration from the public template:

```sh
cp config.example.json config.json
```

Set `owner` to your GitHub login, replace `repositories` with the repository names you want to run, set your GitHub App ID, and adjust the local paths for the App key and Tart executable. The controller currently requires `max_vms: 2`, `cpu_per_vm: 4`, and `memory_mb_per_vm: 8192`; those values are validated at startup. Keep `config.json` out of Git.

Install [Tart](https://github.com/openai/tart/releases) from an official source. If you use an archive, verify its SHA-256 checksum before extracting it. Set `tart_bin` in the Git-ignored `config.json` to the actual executable. In the examples below, `TART_BIN` stands for that path:

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" list
```

Install [Softnet](https://github.com/openai/softnet) to isolate the clones' network (`brew install openai/tools/softnet`). The binary Tart uses must be under `/opt/homebrew/bin`, owned by `root`, and have the SUID bit described by the project. Check its source and path before granting it this privilege. Without Softnet, job clones fail to start.

Create two **stopped** base images. The image versions below are examples; check their current availability and compatibility before use. The macOS download may be tens of gigabytes. The `run` command stays open: run the `exec` and `stop` commands in a **second terminal**.

Linux, terminal A:

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" clone ghcr.io/cirruslabs/ubuntu:24.04 personal-ci-linux-v1
"$TART_BIN" set personal-ci-linux-v1 --cpu 4 --memory 8192
"$TART_BIN" run --no-graphics personal-ci-linux-v1
```

Linux, terminal B while the VM is running:

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" exec -i personal-ci-linux-v1 /bin/bash -s < scripts/bootstrap-linux.sh
"$TART_BIN" stop personal-ci-linux-v1
```

macOS, terminal A:

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" clone ghcr.io/cirruslabs/macos-tahoe-xcode:26.5 personal-ci-macos-v1
"$TART_BIN" set personal-ci-macos-v1 --cpu 4 --memory 8192
"$TART_BIN" run --no-graphics personal-ci-macos-v1
```

macOS, terminal B while the VM is running:

```sh
TART_BIN="$HOME/.local/opt/tart.app/Contents/MacOS/tart"
"$TART_BIN" exec -i personal-ci-macos-v1 /bin/bash -s < scripts/bootstrap-macos.sh
"$TART_BIN" stop personal-ci-macos-v1
```

The Linux bootstrap installs Docker and the ARM64 runner; the macOS bootstrap checks Xcode and installs the ARM64 runner. The runner archives have SHA-256 checksums pinned in the scripts. Restart each image after setup to check the 4 vCPUs, memory, and tools, then leave it stopped. **Never put a token or runner ID in a base image.**

## GitHub access

A dedicated GitHub App needs repository permissions **Actions: read** and **Administration: read/write**. It does not need a webhook or subscribed events; the controller polls the API. Store the downloaded private key on the Mac:

```sh
mkdir -p ~/.config/personal-ci
chmod 700 ~/.config/personal-ci
# Move the downloaded key here without displaying it in the terminal.
chmod 600 ~/.config/personal-ci/github-app.pem
```

In `config.json`, set `repositories`, `github_app.app_id`, and `github_app.private_key_file`. Even if the App is installed for the whole account, the controller requests an installation token limited to the repositories in `repositories` and those two permissions. The key and tokens stay out of images and logs. The [public template](../config.example.json) contains no secrets.

## Start or diagnose the service

Before the first installation:

```sh
python3 -m unittest discover -s tests -v
python3 -m personal_ci --config config.json doctor
python3 -m personal_ci --config config.json once
python3 scripts/install-service.py
```

`once` admits available jobs one time, waits for them to finish, then exits. `install-service.py` installs the LaunchAgent **once**; do not run it again on a host where it is already installed. To inspect an existing service:

```sh
launchctl print gui/$(id -u)/dev.personal-ci.runners
python3 -m personal_ci --config config.json status
```

If a job stays queued, check these in order: Mac is on and a user is logged in, service is `running`, both slots are already occupied, free disk space (40 GiB reserve), job's `runs-on` label, repository is in `repositories`, and App access. The controller admits only `push`, `workflow_dispatch`, `schedule`, and `pull_request`; it ignores `pull_request_target`.

If a job fails, first read its steps in GitHub Actions. For an infrastructure failure, check `controller.err.log`, the VM log listed in `instances.json`, and the Tart VM list. `python3 -m personal_ci --config config.json reconcile` removes entries for clones that no longer exist and marks orphaned clones for inspection. **Inspect the GitHub job and clone before any manual deletion**: the job number recorded at admission alone does not prove which job the runner received.

Clones use Softnet and do not share the host's clipboard or folders. Fork PRs still run untrusted code; do not expose the App key, host secrets, or GitHub write tokens to them.
