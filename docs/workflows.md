# Workflow routing

The controller only accepts `push`, `workflow_dispatch`, and `schedule` jobs from a configured repository. Keep PR validation on GitHub-hosted runners. Use a lane label in each selected repository's own workflow.

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

Replace the project commands with the real test/build commands and pin third-party actions to a commit SHA when promoting a workflow. The Linux VM is ARM64; a Docker image that exists only for x86-64 needs a different image or a separately qualified translation route. Apple compilation uses the macOS lane because Xcode does not run inside Linux.
