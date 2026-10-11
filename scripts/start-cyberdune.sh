#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

for attempt in {1..30}; do
  if docker info >/dev/null 2>&1; then break; fi
  sleep 2
done
docker info >/dev/null

docker compose up -d

# A rebuilt Codespace can retain disconnected bridges from the previous daemon.
# Their duplicate routes and nft NAT rules can intercept the current containers.
# Only clean a linkdown route for our fixed subnet when Docker's current bridge
# exists; never remove a live bridge, a different subnet, or a global policy.
if [[ "${CODESPACES:-false}" == "true" ]]; then
  for network in ctfd_default ctfd_internal; do
    subnet=$(docker network inspect "$network" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}')
    case "$subnet" in 10.203.0.0/24|10.203.1.0/24) ;; *) continue ;; esac
    network_id=$(docker network inspect "$network" --format '{{.Id}}')
    current_bridge=$(docker network inspect "$network" --format '{{index .Options "com.docker.network.bridge.name"}}')
    if [[ -z "$current_bridge" || "$current_bridge" == '<no value>' ]]; then
      current_bridge="br-${network_id:0:12}"
    fi
    ip link show dev "$current_bridge" >/dev/null
    while IFS= read -r route; do
      [[ " $route " == *' linkdown '* ]] || continue
      read -r -a fields <<< "$route"
      stale_bridge=''
      for ((i=0; i<${#fields[@]}-1; i++)); do
        if [[ "${fields[i]}" == dev ]]; then stale_bridge="${fields[i+1]}"; break; fi
      done
      [[ "$stale_bridge" == br-* && "$stale_bridge" != "$current_bridge" ]] || continue
      if command -v iptables-nft >/dev/null; then
        while sudo -n iptables-nft -w -t nat -C POSTROUTING \
          -s "$subnet" ! -o "$stale_bridge" -j MASQUERADE 2>/dev/null; do
          sudo -n iptables-nft -w -t nat -D POSTROUTING \
            -s "$subnet" ! -o "$stale_bridge" -j MASQUERADE
        done
        while IFS= read -r container_ip; do
          [[ -n "$container_ip" ]] || continue
          while sudo -n iptables-nft -w -t raw -C PREROUTING \
            -d "$container_ip" ! -i "$stale_bridge" -j DROP 2>/dev/null; do
            sudo -n iptables-nft -w -t raw -D PREROUTING \
              -d "$container_ip" ! -i "$stale_bridge" -j DROP
          done
        done < <(docker network inspect "$network" --format '{{range .Containers}}{{println .IPv4Address}}{{end}}' | sed 's@/.*@/32@')
      fi
      sudo -n ip route del "$subnet" dev "$stale_bridge"
      echo "Removed stale Codespaces route for $subnet through $stale_bridge."
    done < <(ip -4 route show exact "$subnet")
  done
fi

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
