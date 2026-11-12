# Public HTTPS edge (optional)

This directory holds the code for public dynamic-challenge URLs of the form
`https://<instance-id>.targets.cyberdune.online`. It is **disabled by default**
and is not part of the running CTFd Compose project.

## How it fits together

```
player -> host Nginx (TLS, wildcard cert)
       -> 127.0.0.1:8081 Traefik (Docker provider)
       -> gateway-<identity> container :8080 on ctfd_instance_edge
       -> target container :8080 on its per-instance internal network
```

Edge mode is selected per challenge by the `edge_host`/`edge_network`
`additional` fields that `web_preset.py` adds when `INSTANCE_EDGE_HOST` is set.
In edge mode the gateway publishes no host port and gets Traefik labels; the
instance connection info is the HTTPS URL. Public port mode
(`INSTANCE_PUBLIC_HOST`) and edge mode are mutually exclusive.

## Prerequisites (both are external gates)

1. DNS: add `*.targets` A record pointing to `51.170.136.188` (and optionally
   `targets` itself). The zone currently uses Namecheap BasicDNS.
2. Certificate: a wildcard certificate for `*.targets.cyberdune.online` via
   ACME DNS-01. Namecheap BasicDNS has no certbot DNS plugin, so choose one of:
   - add the `_acme-challenge.targets` TXT record manually for each issuance and
     renewal (`certbot certonly --manual --preferred-challenges dns`), or
   - use the Namecheap API with an API key and whitelisted source IP, or
   - delegate `_acme-challenge.targets` to a DNS provider with an API
     (for example a CNAME to Cloudflare) and use `certbot-dns-cloudflare`.

   Request the certificate with the name `targets.cyberdune.online` so the files
   land in `/etc/letsencrypt/live/targets.cyberdune.online/` as the Nginx
   snippet expects.

## Enable

```bash
# 0. Publish the edge-capable launcher (v6) and point the manager at it.
SCENARIO_ARCH=arm64 scripts/publish-instance-launcher.sh
# then set chall-manager:web_scenario to the published v6 digest.

# 1. Shared edge network (created once; the scenario attaches to it).
docker compose -p cyberdune-edge -f services/edge/docker-compose.edge.yml up -d

# 2. Nginx: copy the snippet and map, then test and reload.
sudo cp services/edge/nginx-targets-map.conf /etc/nginx/conf.d/
sudo cp services/edge/nginx-targets.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl reload nginx

# 3. Let CTFd build edge-mode challenges.
#    Add to the ctfd environment (release overlay or env file):
#      INSTANCE_EDGE_HOST=targets.cyberdune.online
#      INSTANCE_EDGE_NETWORK=ctfd_instance_edge
#    Then recreate only ctfd:
sudo /home/ubuntu/ctfd-compose up -d --no-deps ctfd
```

## Verify before trusting it

- `dig +short test.targets.cyberdune.online` returns the VPS IP.
- `curl -sSI https://<instance-id>.targets.cyberdune.online/` has a valid
  certificate and HSTS.
- Launch, expiry and destroy through CTFd remove the route (Traefik drops the
  router when the gateway container is removed).
- The target still cannot reach Docker, CTFd, Chall-Manager, the database,
  Redis, metadata, or another target.

## Honest limits

- Everything shares one kernel and one Docker daemon. This is not hard isolation
  against a container escape or a malicious privileged build; only trusted
  admins may upload ZIPs/Dockerfiles.
- Traefik mounts the Docker socket read-only. The read-only mount limits writes
  through the filesystem but the Docker API itself is still reachable to a
  compromised Traefik.
- Gateways are dual-homed (instance network + shared edge network). A target can
  reach its own gateway only; gateways have `net.ipv4.ip_forward=0` and only
  proxy to their own target, so they do not route between instances.
