#!/usr/bin/env bash
# Build the verified v0.6.6 release for the ARM64 instance host, without changing services.
set -euo pipefail
[[ "$(uname -m)" == aarch64 ]] || { echo 'This override is for an ARM64 host.'; exit 1; }
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
archive=chall-manager-0.6.6.tar.gz
curl --fail --location --silent --show-error "https://github.com/ctfer-io/chall-manager/releases/download/v0.6.6/$archive" -o "$work/$archive"
echo "831a81993e00c293ccc42d1081d044474731b015a82d0b3f442660c9446e9f79  $work/$archive" | sha256sum --check
tar -xzf "$work/$archive" -C "$work"
cp "$repo/services/native-manager/Dockerfile" "$work/Dockerfile.native"
cp "$repo/services/native-manager/disable-telemetry.patch" "$work/disable-telemetry.patch"
sudo docker build -f "$work/Dockerfile.native" -t cyberdune/chall-manager:v0.6.6-arm64-polish "$work"
echo 'Built. Add docker-compose.native.yml last in the existing Compose file list.'
