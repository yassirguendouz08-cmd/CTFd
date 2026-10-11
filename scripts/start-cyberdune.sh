#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Some Codespaces hosts retain a legacy FORWARD policy that blocks sibling
# containers. Preserve the known project-only workaround when it is available.
if [[ "${CODESPACES:-false}" == "true" ]] && command -v iptables-legacy >/dev/null; then
  for subnet in 10.203.0.0/24 10.203.1.0/24; do
    if ! sudo -n iptables-legacy -C FORWARD \
      -s "$subnet" -d "$subnet" -j ACCEPT 2>/dev/null; then
      sudo -n iptables-legacy -I FORWARD 1 \
        -s "$subnet" -d "$subnet" -j ACCEPT
    fi
  done
fi

for attempt in {1..30}; do
  if docker info >/dev/null 2>&1; then break; fi
  sleep 2
done
docker info >/dev/null

docker compose up -d
echo "CyberDune is starting. Open forwarded port 80 once CTFd is ready."
