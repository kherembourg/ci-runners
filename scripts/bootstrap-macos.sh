#!/bin/bash
set -euo pipefail

# Run once inside a stopped-base macOS ARM64 Tart VM as the admin user.
test "$(uname -m)" = arm64
xcodebuild -version
runner_version=2.337.0
runner_sha256=5a2cd92908a93d7276a194e1de6008099f3e7946f3f8e14aa7a1a7b4a31fdec2
archive="actions-runner-osx-arm64-${runner_version}.tar.gz"
url="https://github.com/actions/runner/releases/download/v${runner_version}/${archive}"
mkdir -p "$HOME/actions-runner"
curl -fL --retry 3 -o "/tmp/${archive}" "$url"
printf '%s  %s\n' "$runner_sha256" "/tmp/${archive}" | shasum -a 256 -c -
tar -xzf "/tmp/${archive}" -C "$HOME/actions-runner"
rm "/tmp/${archive}"
"$HOME/actions-runner/bin/Runner.Listener" --version
