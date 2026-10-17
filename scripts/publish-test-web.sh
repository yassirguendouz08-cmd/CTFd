#!/usr/bin/env bash
# Run on the Linux Docker worker. Publishes a reusable scenario and a test image.
set -euo pipefail
umask 077

name=${1:-cookie-mirage}
if [[ ! "$name" =~ ^[a-z][a-z0-9-]{0,50}$ ]]; then
  printf 'Use a challenge folder name containing lowercase letters, numbers and hyphens.\n' >&2
  exit 1
fi
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
challenge="$repo/challenges/$name"
test -f "$challenge/Dockerfile" || { printf 'Missing %s/Dockerfile\n' "$challenge" >&2; exit 1; }
command -v docker >/dev/null
command -v openssl >/dev/null
curl --fail --silent --show-error http://127.0.0.1:5001/v2/ >/dev/null
sudo docker info >/dev/null

image="cyberdune/$name:v1"
sudo docker build --tag "$image" "$challenge"

# The manager on the Oracle ARM64 VPS runs AMD64 under QEMU. Its scenario
# executable must also be AMD64, although target images run natively on ARM64.
scenario_arch=${SCENARIO_ARCH:-amd64}
case "$scenario_arch" in amd64|arm64) ;; *) printf 'Unsupported SCENARIO_ARCH\n' >&2; exit 1 ;; esac
artifact_tag="web-container:v1-$scenario_arch"
temp_dir=$(mktemp -d)
trap 'sudo rm -f -- "$temp_dir/main" "$temp_dir/Pulumi.yaml"; rmdir -- "$temp_dir"' EXIT

sudo docker build --file "$repo/scenarios/web-container/Dockerfile" \
  --build-arg "SCENARIO_ARCH=$scenario_arch" \
  --output "type=local,dest=$temp_dir" "$repo/scenarios/web-container"

oras_image=ghcr.io/oras-project/oras:v1.3.0
sudo docker run --rm --user 0 --network host \
  --mount "type=bind,src=$temp_dir,dst=/work,readonly" --workdir /work \
  "$oras_image" push --plain-http "localhost:5001/scenarios/$artifact_tag" \
  --artifact-type application/vnd.ctfer-io.scenario \
  main:application/vnd.ctfer-io.file Pulumi.yaml:application/vnd.ctfer-io.file

digest=$(sudo docker run --rm --network host "$oras_image" resolve --plain-http \
  "localhost:5001/scenarios/$artifact_tag")
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]] || { printf 'Invalid scenario digest\n' >&2; exit 1; }

settings_dir="$HOME/.config/cyberdune/challenges"
mkdir -p -- "$settings_dir"
seed_file="$settings_dir/$name.seed"
if [ ! -s "$seed_file" ]; then
  openssl rand -hex 32 > "$seed_file"
fi
chmod 600 "$seed_file"
seed=$(cat -- "$seed_file")
[[ "$seed" =~ ^[a-f0-9]{64}$ ]] || { printf 'Invalid seed file: %s\n' "$seed_file" >&2; exit 1; }
printf '\nReady to create a HIDDEN dynamic_iac challenge.\n'
printf 'Scenario: scenario-registry:5000/scenarios/%s@%s\n' "$artifact_tag" "$digest"
printf '\nAdvanced → Challenge configuration: add these three rows, then click Apply:\n'
printf 'image      %s\nport       8080\nflag_seed  %s\n' "$image" "$seed"
printf '\nSharing: Disabled; Mana: 1; Timeout: 600 (seconds); Pool Min/Max: 0/0.\n'
printf 'Leave static flags empty. Keep the seed private and retain it for updates.\n'
printf 'Targets bind to VPS loopback only; see docs/WEB-INSTANCE-TEST.md for SSH access.\n'
