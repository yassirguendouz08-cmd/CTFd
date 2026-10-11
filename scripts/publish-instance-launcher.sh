#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
arch=${SCENARIO_ARCH:-amd64}
case "$arch" in amd64|arm64) ;; *) echo "Unsupported architecture"; exit 1 ;; esac
tag="web-container:v2-$arch"
artifact=$(mktemp -d)
trap 'sudo rm -f -- "$artifact/main" "$artifact/Pulumi.yaml"; rmdir -- "$artifact"' EXIT
sudo docker build -f "$repo/scenarios/web-container/Dockerfile" --build-arg "SCENARIO_ARCH=$arch" --output "type=local,dest=$artifact" "$repo/scenarios/web-container"
oras=ghcr.io/oras-project/oras:v1.3.0
sudo docker run --rm --user 0 --network host --mount "type=bind,src=$artifact,dst=/work,readonly" --workdir /work "$oras" push --plain-http "localhost:5001/scenarios/$tag" --artifact-type application/vnd.ctfer-io.scenario main:application/vnd.ctfer-io.file Pulumi.yaml:application/vnd.ctfer-io.file
digest=$(sudo docker run --rm --network host "$oras" resolve --plain-http "localhost:5001/scenarios/$tag")
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]] || { echo "Invalid scenario digest"; exit 1; }
cd "$repo"
sudo docker compose exec -T ctfd python scripts/configure-web-launcher.py "scenario-registry:5000/scenarios/$tag@$digest"
