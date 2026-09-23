# Workflow guide

Your application workflows belong in **each application's repository**, under `.github/workflows/`. This repository supplies the controller, VM images, and three workflows that test the runner infrastructure. Add every application repository to `repositories` in your local `config.json` and install your GitHub App for those repositories.

## Choose a lane

The controller recognizes the four labels in the [example configuration](../config.example.json). A label selects an operating system and separates pull request (PR) jobs from push, scheduled, and manually started jobs. These are self-hosted VMs; GitHub still handles triggers, queues, logs, statuses, and artifacts.

| Event | Linux ARM64 with Docker | macOS ARM64 with Xcode |
| --- | --- | --- |
| Push, schedule, or manual | `personal-ci-linux-arm64` | `personal-ci-macos-arm64` |
| Pull request | `personal-ci-linux-arm64-pr` | `personal-ci-macos-arm64-pr` |

Use Linux for web, JavaScript, JVM, and Docker jobs that support ARM64. Use macOS for Xcode and iOS jobs. Android and Kotlin Multiplatform builds may need either OS depending on their toolchains; qualify the chosen VM before routing production jobs to it. The example configuration permits two simultaneous VMs, so additional jobs wait in GitHub's queue. A job with `needs` also waits for its dependency.

## Workflows in this repository

| Workflow | Trigger | What runs | Lane |
| --- | --- | --- | --- |
| [`verify.yml`](../.github/workflows/verify.yml) | Push or PR | Python unit tests and bootstrap script syntax checks | Linux; Linux PR for a PR |
| [`linux-smoke.yml`](../.github/workflows/linux-smoke.yml) | Manual | Checks CPU, memory, and Docker | Linux |
| [`macos-smoke.yml`](../.github/workflows/macos-smoke.yml) | Manual | Checks CPU, memory, Xcode, and Swift | macOS |

A smoke test checks that a VM can accept a job and has its basic tools. It does not test your application. The controller currently requires two 4-vCPU, 8-GiB VM slots; the smoke workflows check that size.

## Add a workflow to your repository

For a workflow that runs on both push and PR, choose a label based on the event:

```yaml
name: CI
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ${{ github.event_name == 'pull_request' && 'personal-ci-linux-arm64-pr' || 'personal-ci-linux-arm64' }}
    steps:
      - uses: actions/checkout@v4
      - run: ./scripts/test.sh
```

Replace the final command with your project's test or build command. For an iOS/Xcode job, use the corresponding `personal-ci-macos-arm64` and `personal-ci-macos-arm64-pr` labels. Workflows that only run on a PR may use the PR label directly; scheduled or manually started workflows use the regular label.

Keep `permissions` as narrow as each job allows. Fork PRs run untrusted code in disposable VMs; do not pass host secrets or write-capable tokens to those jobs. The controller does not admit `pull_request_target` jobs.

After adding the repository to the local allowlist and GitHub App installation, trigger a job and inspect its runner, status, and logs in GitHub Actions. If it stays queued or fails before your application steps, use the [operations guide](operations.md) and the smoke workflows above. Record the evidence for your host in the [qualification checklist](qualification.md).
