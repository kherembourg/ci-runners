# Personal CI runners

Disposable GitHub Actions runners for an Apple Silicon Mac. A job runs in a fresh Tart VM and the VM is removed when the job ends. The Linux ARM64 lane has Docker for JavaScript, web, JVM, and Android build work. The macOS ARM64 lane has Xcode for Apple and Kotlin Multiplatform targets.

The fleet admits at most **two simultaneous VMs**, each with **4 vCPUs and 8 GiB RAM**. GitHub Actions remains the queue. A small host controller polls only named personal repositories and creates repository-level just-in-time runners. It admits only `push`, `workflow_dispatch`, and `schedule` jobs whose source repository matches the configured repository. Public fork pull requests are deliberately excluded.

This repository contains no host credentials. Copy `config.example.json` to an ignored `config.json` on the Mac, set the selected repository names and an absolute credential-file path, and follow [operations](docs/operations.md). The controller credential needs Actions read and Administration write access to only the selected repositories. Keep it outside Git with mode `0600`.

Use `personal-ci-linux-arm64` for Linux work and `personal-ci-macos-arm64` for Xcode work. See [workflow examples](docs/workflows.md). The runner software and guest tools are installed into stopped base images; no registration token is baked into an image.

```sh
python3 -m unittest discover -s tests -v
python3 -m personal_ci --config config.json doctor
python3 -m personal_ci --config config.json serve
```

The service preserves an ownership ledger and per-instance logs. If a controller crash leaves a VM with uncertain job state, it reserves capacity and requires inspection before deletion. Android emulators, iOS simulators, signing, and deployments are not claimed by the initial lane labels.

Tart is provided by [the Tart project](https://tart.run/); GitHub's [self-hosted runner documentation](https://docs.github.com/en/actions/reference/runners/self-hosted-runners) describes the JIT runner API and security model. This repository is independently authored and MIT licensed.
