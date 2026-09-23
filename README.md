# Personal CI runners

Disposable GitHub Actions runners for an Apple Silicon Mac. A job runs in a fresh Tart VM and the VM is removed when the job ends. The Linux ARM64 lane has Docker for JavaScript, web, and JVM work. The macOS ARM64 lane has Xcode and native Android build tools for Apple, Android, and Kotlin Multiplatform targets.

**Status:** both lanes passed real GitHub Actions smoke jobs, including Docker on Linux and Xcode on macOS. A simultaneous Linux/macOS run also passed. See the qualification ledger before using a lane for a new workload.

See the [qualification ledger](docs/qualification.md) for observed host and workflow results.

The fleet admits at most **two simultaneous VMs**, each with **4 vCPUs and 8 GiB RAM**. GitHub Actions remains the queue. A small host controller polls only named personal repositories and creates repository-level just-in-time runners. Trusted `push`, `workflow_dispatch`, and `schedule` jobs use the standard lane labels; `pull_request` jobs use separate PR labels, including for fork PRs. `pull_request_target` is never admitted.

This repository contains no host credentials. Copy `config.example.json` to an ignored `config.json` on the Mac, set the selected repository names and your dedicated GitHub App ID, and follow [operations](docs/operations.md). Give the App Actions read and Administration write permissions; the controller requests installation tokens for only its configured repositories. Keep the private key outside Git with mode `0600`.

Use `personal-ci-linux-arm64` for trusted Linux work and `personal-ci-macos-arm64` for trusted Xcode work. PR jobs use `personal-ci-linux-arm64-pr` and `personal-ci-macos-arm64-pr`. See [workflow examples](docs/workflows.md). Every job runs in a disposable VM without host shares; no registration token is baked into an image. Fork PR code is untrusted and still carries VM escape and network abuse risk, so keep host credentials outside the guest and do not grant PR jobs secrets or write permissions.

```sh
python3 -m unittest discover -s tests -v
python3 -m personal_ci --config config.json doctor
python3 -m personal_ci --config config.json serve
```

The service preserves an ownership ledger and per-instance logs. If a controller crash leaves a VM with uncertain job state, it reserves capacity and requires inspection before deletion. Android emulators, iOS simulators, signing, and deployments are not claimed by the initial lane labels.

Tart is provided by [the Tart project](https://tart.run/); GitHub's [self-hosted runner documentation](https://docs.github.com/en/actions/reference/runners/self-hosted-runners) describes the JIT runner API and security model. This repository is independently authored and MIT licensed.
