#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ $(id -u) != 0 ]]; then
  echo "Run once with sudo bash scripts/install-instance-builder.sh"
  exit 1
fi
jobs="$repo/.data/CTFd/uploads/instance-builds"
uid=$(stat -c %u "$repo/.data/CTFd/uploads")
gid=$(stat -c %g "$repo/.data/CTFd/uploads")
install -d -m 750 -o "$uid" -g "$gid" "$jobs"
manager=$(cd "$repo" && docker compose ps -q chall-manager)
if [[ -n "$manager" ]]; then
  state_volume=$(docker inspect "$manager" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/chall-manager"}}{{.Name}}{{end}}{{end}}')
  if [[ -n "$state_volume" ]]; then
    docker run --rm --network none -v "$state_volume:/state" alpine:3.23 mkdir -p /state/pulumi-state
  fi
fi
cat > /etc/systemd/system/cyberdune-instance-builder.service <<EOF
[Unit]
Description=CyberDune admin ZIP instance builder
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 "$repo/services/instance-builder/worker.py" --jobs "$jobs" --uid $uid --gid $gid
Restart=on-failure
RestartSec=3
UMask=0027
StateDirectory=cyberdune-instance-builder
Environment=DOCKER_CONFIG=/var/lib/cyberdune-instance-builder
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$jobs

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now cyberdune-instance-builder.service
systemctl restart cyberdune-instance-builder.service
echo "ZIP builder installed and running."
