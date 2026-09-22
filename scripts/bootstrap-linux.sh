#!/usr/bin/env bash
set -euo pipefail

# Run once inside a stopped-base Ubuntu ARM64 Tart VM as the admin user.
test "$(uname -m)" = aarch64
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$(id -un)"

runner_version=2.337.0
runner_sha256=9b1dc70626422526e3c94767cf024896beb15da5342a3f4819bf2feac13e0393
archive="actions-runner-linux-arm64-${runner_version}.tar.gz"
url="https://github.com/actions/runner/releases/download/v${runner_version}/${archive}"
mkdir -p "$HOME/actions-runner"
curl -fL --retry 3 -o "/tmp/${archive}" "$url"
printf '%s  %s\n' "$runner_sha256" "/tmp/${archive}" | sha256sum -c -
tar -xzf "/tmp/${archive}" -C "$HOME/actions-runner"
rm "/tmp/${archive}"
"$HOME/actions-runner/bin/installdependencies.sh" || sudo "$HOME/actions-runner/bin/installdependencies.sh"
docker --version
"$HOME/actions-runner/bin/Runner.Listener" --version
sync
