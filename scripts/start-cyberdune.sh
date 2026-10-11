#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

for attempt in {1..30}; do
  if docker info >/dev/null 2>&1; then break; fi
  sleep 2
done
docker info >/dev/null

docker compose up -d

# Apply after Docker has created its chains. A FORWARD rule below Docker's
# jumps cannot override an earlier DROP. Keep only project-to-project traffic
# allowed, at the front of Docker's user chain (or FORWARD on older hosts).
if [[ "${CODESPACES:-false}" == "true" ]] && command -v iptables-legacy >/dev/null; then
  chain=DOCKER-USER
  if ! sudo -n iptables-legacy -w -S "$chain" >/dev/null 2>&1; then
    chain=FORWARD
  fi
  for subnet in 10.203.0.0/24 10.203.1.0/24; do
    while sudo -n iptables-legacy -w -C "$chain" \
      -s "$subnet" -d "$subnet" -j ACCEPT 2>/dev/null; do
      sudo -n iptables-legacy -w -D "$chain" \
        -s "$subnet" -d "$subnet" -j ACCEPT
    done
    sudo -n iptables-legacy -w -I "$chain" 1 \
      -s "$subnet" -d "$subnet" -j ACCEPT
  done
fi
echo "CyberDune is starting. Open forwarded port 80 once CTFd is ready."
