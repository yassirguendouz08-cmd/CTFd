#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
arch=${SCENARIO_ARCH:-amd64}
sudo docker build -t cyberdune/instance-gateway:v1 "$repo/services/instance-gateway"
case "$arch" in amd64|arm64) ;; *) echo "Unsupported architecture"; exit 1 ;; esac
tag="web-container:v4-$arch"
artifact=$(mktemp -d)
trap 'sudo rm -f -- "$artifact/main" "$artifact/Pulumi.yaml"; rmdir -- "$artifact"' EXIT
if [[ "${USE_CACHED_LAUNCHER_BUILDER:-0}" == 1 ]]; then
  sudo docker run --rm --network none -e "SCENARIO_ARCH=$arch" \
    --mount "type=bind,src=$repo/scenarios/web-container,dst=/src,readonly" \
    --mount "type=bind,src=$artifact,dst=/out" --workdir /src cyberdune/launcher-build-cache \
    sh -c 'go test ./... && CGO_ENABLED=0 GOOS=linux GOARCH="$SCENARIO_ARCH" go build -trimpath -o /out/main . && cp Pulumi.yaml /out/Pulumi.yaml'
else
  sudo docker build -f "$repo/scenarios/web-container/Dockerfile" --build-arg "SCENARIO_ARCH=$arch" --output "type=local,dest=$artifact" "$repo/scenarios/web-container"
fi
oras=ghcr.io/oras-project/oras:v1.3.0
sudo docker run --rm --user 0 --network host --mount "type=bind,src=$artifact,dst=/work,readonly" --workdir /work "$oras" push --plain-http "localhost:5001/scenarios/$tag" --artifact-type application/vnd.ctfer-io.scenario main:application/vnd.ctfer-io.file Pulumi.yaml:application/vnd.ctfer-io.file
digest=$(sudo docker run --rm --network host "$oras" resolve --plain-http "localhost:5001/scenarios/$tag")
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]] || { echo "Invalid scenario digest"; exit 1; }
cd "$repo"
sudo docker compose exec -T ctfd python scripts/configure-web-launcher.py "scenario-registry:5000/scenarios/$tag@$digest"
