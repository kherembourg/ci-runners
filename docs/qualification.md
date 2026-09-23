# Qualification checklist

Use this checklist to validate **your own Mac and repositories**. A successful run on one host does not establish that a different host, image version, toolchain, or application will work. Record dates, image versions, and GitHub Actions run links in your own operational notes; do not put credentials in this repository.

## Host and capacity

- [ ] Confirm the Mac has enough CPU, memory, and disk space for the configured number and size of VMs. The [example configuration](../config.example.json) allows two concurrent 4-vCPU, 8-GiB guests and reserves 40 GiB of free disk space.
- [ ] Keep the host powered, connected to the network, and logged in while CI should run. Confirm the LaunchAgent reports `state = running`.
- [ ] Run `python3 -m personal_ci --config config.json doctor` on the host. Confirm that the expected images and GitHub App key file are present.

## Linux VM

- [ ] Bootstrap and stop the Linux base image as described in the [operations guide](operations.md).
- [ ] Start a disposable clone and check its CPU count, memory, network access to GitHub, and Docker with an ARM64 container.
- [ ] Run [Linux VM smoke](../.github/workflows/linux-smoke.yml) from GitHub Actions. Confirm the job completes on the Linux label and that its runner and VM clone are removed afterward.
- [ ] Run one real Linux application build or test. Check that every tool and Docker image it uses supports ARM64.

## macOS VM

- [ ] Bootstrap and stop the macOS base image as described in the [operations guide](operations.md).
- [ ] Start a disposable clone and check its CPU count, memory, Xcode, and Swift versions.
- [ ] Run [macOS VM smoke](../.github/workflows/macos-smoke.yml) from GitHub Actions. Confirm the job completes on the macOS label and that its runner and VM clone are removed afterward.
- [ ] For iOS work, boot the simulator your project uses and run its tests or build. For Android or Kotlin Multiplatform work, verify the exact Gradle and Android toolchain on the chosen VM.

## Queue, PRs, and recovery

- [ ] Trigger jobs concurrently and confirm no more than `max_vms` VMs run at once; later jobs should remain queued.
- [ ] Open a PR and confirm its jobs use the matching `-pr` lanes. Test a fork PR separately if you intend to accept external contributions. Never expose host secrets or write-capable tokens to untrusted PR code.
- [ ] Restart the controller with a job in progress and inspect its ownership state before any manual cleanup. Confirm orphaned or uncertain clones continue to reserve capacity until reconciled.
- [ ] Check the GitHub Actions logs, controller logs, and VM logs after a failed job. Use the [operations guide](operations.md) to distinguish VM failures from application failures.

Unit tests cover controller logic such as event filtering, capacity, and cleanup, but they cannot replace these end-to-end checks on your own hardware and GitHub installation.
