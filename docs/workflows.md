# Workflow routing

The controller accepts trusted `push`, `workflow_dispatch`, and `schedule` jobs from configured repositories, plus `pull_request` jobs from those repositories and their forks. PR jobs use separate lane labels and disposable VMs. `pull_request_target` is excluded. Use a lane label in each selected repository's own workflow.

For a workflow that runs on both push and PR, select the PR lane with `runs-on: ${{ github.event_name == 'pull_request' && 'personal-ci-linux-arm64-pr' || 'personal-ci-linux-arm64' }}`. Replace `linux` with `macos` for Xcode and Android Gradle Plugin builds. Keep PR permissions read-only and never pass secrets to code checked out from a fork.

Linux example for a Node project:

```yaml
name: Linux build
on:
  push:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  build:
    runs-on: personal-ci-linux-arm64
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v4
      - run: docker run --rm -v "$PWD:/work" -w /work node:22-bookworm bash -lc 'npm ci && npm test && npm run build'
```

macOS example for an Apple target:

```yaml
name: Apple build
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  build:
    runs-on: personal-ci-macos-arm64
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - run: xcodebuild -version
      - run: ./gradlew :shared:compileKotlinIosArm64
```

Replace the project commands with the real test/build commands and pin third-party actions to a commit SHA when promoting a workflow. The Linux VM is ARM64; a Docker image that exists only for x86-64 needs a different image or a separately qualified translation route. Route Android Gradle Plugin builds to the macOS ARM64 lane because its AAPT2 Linux artifact is x86-64. Apple compilation also uses the macOS lane because Xcode does not run inside Linux.
