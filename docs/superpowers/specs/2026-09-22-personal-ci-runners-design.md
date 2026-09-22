# Personal CI runners design

## Goal

Run GitHub Actions jobs from an explicit list of personal repositories on an Apple Silicon MacBook Pro. A job runs in a disposable Tart VM. Linux jobs may use Docker for JavaScript, web, and JVM builds; macOS jobs use Xcode and native Android build tools for Apple and Android targets in Kotlin Multiplatform. The infrastructure repository is public, contains no credentials or private host details, and is independently written.

## Host and capacity

The target host is an Apple M1 Pro with 8 CPU cores, 32 GiB RAM, and about 281 GiB free at design time. Admit at most two VMs. Each VM has exactly 4 vCPUs and 8 GiB RAM, so the maximum guest allocation is 8 vCPUs and 16 GiB. Admission is limited by both the configured slot count and available disk/memory; a failed preflight leaves the job queued. Battery or sleep can pause service; production operation requires AC power and a wakeful host.

## Components

`personal_ci` is a Python standard-library host controller. A JSON config names only allowed `kHerembourg` repositories, labels, VM base images, resource limits, polling interval, and a credential-file path outside Git. GitHub Actions is the queue. The controller lists queued and in-progress workflow runs and their queued jobs; it only handles selected labels and trusted `push`, `workflow_dispatch`, and `schedule` events from the configured repository. It calls GitHub's repository-level JIT runner endpoint after a VM is ready. The registration payload is short-lived and sent only into that job's VM.

`TartProvider` clones a stopped, versioned Linux or macOS base, sets 4 CPU and 8 GiB, boots headless, waits for guest access, and starts the GitHub runner. The Linux base has Docker Engine and the ARM64 Actions runner archive. The macOS base has Xcode and the ARM64 runner archive. Base images contain no credentials, checkout, or host mount. Job VMs never mount the host home, SSH agent, Tailscale socket, or controller credential.

The controller keeps an owned-instance ledger and a per-instance log outside disposable VMs. It does not delete an instance of unknown ownership or one whose job state is uncertain. On restart, owned live instances reserve capacity until reconciled. On normal completion, it exports runner diagnostics, stops and deletes only its own clone, and clears the reservation. The host service runs under a dedicated launchd label as the local user.

## Security and repository scope

The public repository contains source, tests, image bootstrap scripts, workflow examples, docs, and non-secret config examples. A dedicated GitHub App has Actions read and Administration write permissions. Its private key stays on the Mac at mode 0600; installation tokens are short-lived and scoped to the explicit repository allowlist, even if the App installation itself covers more repositories. The controller never reads or routes repositories outside its allowlist. Public-fork PR jobs are excluded. Workflow examples require a distinctive lane label and restrict permissions by default. No employer names, paths, identifiers, tokens, or code belong in this repository.

## Validation

Unit tests cover config validation, repository/job filtering, capacity admission, JIT request shape, lifecycle cleanup, and restart behavior. A local fake GitHub/Tart integration run proves one Linux and one macOS job can overlap but a third waits. Host preflight proves the installed Tart version, VM image versions, Docker in Linux, Xcode in macOS, runner startup, and exact 4-vCPU/8-GiB shape. A GitHub workflow smoke job in each lane proves actual registration and cleanup. Image and service installation are reported separately from successful GitHub workload evidence.

## Scope

Initial workloads are command-line builds and tests. Android emulator and iOS simulator suites need separate measured qualification before labels claim them. Signing and deployment are outside this first rollout.
