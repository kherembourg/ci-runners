# Personal CI runners implementation plan

> Historical implementation plan from 2026-09-22. The current runner architecture and workflow routing are documented in the [README](../../../README.md) and [workflow map](../../workflows.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and qualify a public, independent GitHub Actions runner fleet on one Apple Silicon Mac with disposable Linux and macOS VMs.

**Architecture:** A Python host controller polls selected repositories, admits at most two 4-vCPU/8-GiB jobs, and creates a repository-level JIT runner in a fresh Tart clone. The clone and its credentials are removed after the job; logs and ownership state remain on the host.

**Tech Stack:** Python 3.9 standard library, Tart, Docker Engine in Ubuntu ARM64, macOS/Xcode Tart image, GitHub Actions REST API, launchd, unittest.

---

### Task 1: Repository contracts

**Files:** `README.md`, `LICENSE`, `.gitignore`, `config.example.json`, `docs/workflows.md`.

- [ ] Write the public configuration schema and workflow examples for both labels, with selected-repository allowlist and trusted event policy.
- [ ] Document the exact 4-vCPU/8-GiB/two-VM budget, power/sleep limitation, credential permissions, and no-secret public repository rule.
- [ ] Run `git diff --check` and scan tracked content for private organization names and credential patterns.
- [ ] Commit the contracts.

### Task 2: GitHub discovery and JIT API

**Files:** `personal_ci/github.py`, `personal_ci/config.py`, `tests/test_github.py`.

- [ ] Write failing tests for invalid config, untrusted runs, label matching, duplicate jobs, API errors, and JIT request body.
- [ ] Implement validated config parsing and an authenticated GitHub REST client with bounded timeouts and pagination.
- [ ] Run `python3 -m unittest discover -s tests -v`; fix failures and commit.

### Task 3: Capacity and lifecycle

**Files:** `personal_ci/fleet.py`, `personal_ci/tart.py`, `personal_ci/state.py`, `tests/test_fleet.py`, `tests/test_tart.py`.

- [ ] Write failing tests for two simultaneous jobs, third-job deferral, failed VM start, cleanup after completion, and restart reconciliation.
- [ ] Implement owned clone names, atomic state, exact VM shape, guest runner launch, preserved logs, and conservative cleanup.
- [ ] Run focused unit tests and commit.

### Task 4: CLI and host packaging

**Files:** `personal_ci/__main__.py`, `scripts/bootstrap-linux.sh`, `scripts/bootstrap-macos.sh`, `deploy/local.personal-ci.plist`, `docs/operations.md`.

- [ ] Add `doctor`, `once`, and `serve` commands; test actionable errors and masked credentials.
- [ ] Add guest bootstrap scripts that install a SHA-256 verified ARM64 Actions runner and Linux Docker Engine or validate macOS Xcode.
- [ ] Add a launchd service template and explicit install/start/stop instructions.
- [ ] Run tests and shell syntax checks; commit.

### Task 5: Host qualification

**Files:** `docs/qualification.md` and host-local ignored runtime files only.

- [ ] Install Tart from its official Homebrew tap on the authorized Mac.
- [ ] Fetch versioned Ubuntu and macOS Xcode images, make stopped prepared bases, and prove 4 CPU/8 GiB inside one clone of each.
- [ ] Verify Docker inside Linux and Xcode/Swift inside macOS; record image versions, disk use, and cleanup.
- [ ] Stop if image compatibility, login keychain, or disk capacity blocks qualification; report exact evidence.

### Task 6: GitHub connection and smoke

**Files:** `docs/qualification.md`, selected personal repository workflows as authorized.

- [ ] Store a credential restricted to selected personal repositories outside Git at mode 0600.
- [ ] Start the host service, observe a Linux smoke job and a macOS smoke job through GitHub Actions, and verify both clones are removed.
- [ ] Run a two-job overlap and third-job deferral test, then record GitHub run links and memory/disk measurements.
- [ ] Scan public content again, create and push `kHerembourg/ci-runners` as a public repository, and verify its visibility and contents.
