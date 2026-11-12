# Public Dynamic Challenge Readiness

This note describes the local application changes and the remaining deployment
work. Nothing in this document changes the running VPS.

## Session cookie and host separation

CTFd now enables `SESSION_COOKIE_SECURE` when its configured `PUBLIC_ORIGIN`
uses HTTPS (or when the explicit security config is true). `HttpOnly` remains
enabled, `SameSite=Lax` remains the default, and no cookie `Domain` is set.
Configure the platform origin as `https://ctf.cyberdune.online` and leave
`SESSION_COOKIE_DOMAIN` unset. The platform cookie is then host-only for
`ctf.cyberdune.online`.

Use `targets.cyberdune.online` for public challenge endpoints. It is a sibling
host, not a subdomain beneath `ctf.cyberdune.online`, and the host-only CTFd
cookie will not be sent to it. Do not set a parent-domain cookie such as
`.cyberdune.online`. Public endpoint traffic from the current scenario is
plain HTTP (`http://targets.cyberdune.online:<port>/`); this does not provide
HTTPS to challenge apps.

## New and existing challenge metadata

The ZIP upload and “New web challenge” preset read `INSTANCE_PUBLIC_HOST` when
creating a challenge and save it as `additional.public_host`. Existing
challenge configuration is not rewritten. The scenario launcher validates
the public host, binds the gateway on `0.0.0.0`, reads the actual Docker-published
port, and returns a URL containing that host and port. If an existing challenge
must be switched to public mode, back it up, update only
`additional.public_host` through the existing CTFd/Chall-Manager challenge
configuration workflow, and verify the stored challenge’s additional config
before allowing player launches. Do not edit its other `additional` keys.

The eventual private production environment needs:

```dotenv
PUBLIC_ORIGIN=https://ctf.cyberdune.online
INSTANCE_PUBLIC_HOST=targets.cyberdune.online
```

Do not apply these values to production until DNS, host firewall, Oracle
firewall, cookie response, and isolation review are complete. Leave
`SESSION_COOKIE_DOMAIN` unset.

## Bounded port allocation (local implementation; review required)

The v5 `web-container` scenario uses the Pulumi Docker provider's actual
single-integer `External` field and passes an explicit reserved port to it.
The default inclusive range is `20000-20127`; configure `INSTANCE_PORT_MIN`,
`INSTANCE_PORT_MAX`, and `INSTANCE_PORT_STATE_FILE` consistently for CTFd and
Chall-Manager. The state file and its lock must live on the manager's persistent
`instance_state` volume, shared by every manager process. Newly created public
presets also persist those values in `additional.port_min`, `port_max`, and
`port_state_file`; existing challenge metadata is deliberately not rewritten.
Existing challenges need to be backed up and updated through the supported
admin configuration workflow, and their scenario reference must use the v5
artifact before testing public launches.

The allocator uses a process-shared Linux `flock`, an atomic durable JSON
ledger, and Docker labels to reconcile reservations after restarts. It skips
ports already reserved in its ledger, published by any Docker container, or
reported unavailable in the manager container's own network namespace. It
checks the actual gateway binding before returning a URL and refuses to
release a lease while a matching or port-owning container remains. Abandoned
pending leases are eligible for recovery after 30 minutes; active leases are
recovered on a subsequent allocation after Docker confirms the container is
gone and the port appears free.

**Collision handling:** the free-socket probe executes inside the manager
container, not the Docker host network namespace, and the Docker container list
does not report host processes that are not containers. A host listener can
therefore claim the selected port between preflight and Docker's bind. The
scenario treats Docker's own bind error (`port is already allocated` or
`address already in use` for the reserved port) as the authoritative signal: it
force-removes its failed gateway container by its deterministic name, releases
the lease only after Docker confirms that no instance container still carries
the identity/port label, reserves another port, and retries, up to three
attempts. Any other startup error (image pull, health check) is not retried, and
a lease that cannot be released safely is kept rather than dropped.

Reservations are never released from the delete path itself. Chall-Manager's
API delete skips metadata removal when `stack.Down` fails, but its janitor path
(`pkg/iac/update.go`) removes instance metadata even then, so Docker labels are
the only trustworthy authority. Cleanup is therefore reconciliation-based: a
lease is reclaimed on a later allocation once Docker shows no container for that
identity and the port is free.

**Docker Desktop Phase 6 integration test (completed; production limits
remain):** Before this test, the retry path was covered only by unit tests of
the decision logic because this workstation had no Docker engine. An isolated
Docker Desktop test now verifies the real bind-conflict path:

- The offline Go compile-only gate passed before any Docker resources were
  created.
- Docker returned a real bind conflict on port `25000`: `Bind for
  0.0.0.0:25000 failed: port is already allocated`.
- `isPortBindConflict` classified the error as a bind conflict for `25000`.
- The allocator excluded `25000` and successfully retried on `25002`.
- The retried gateway became healthy.
- Traffic through the gateway returned the expected HTTP response.
- The lease transitioned from `pending` to `active`.
- Test-owned containers, network, image, labels, and published ports were
  removed, and the temporary run directory was removed.
- The 10 MongoDB containers and the checked `mongodb-network` properties
  remained unchanged: container name, ID, state, `StartedAt`, published ports,
  attached networks; network ID and attached containers. This is a property
  check, not a byte-for-byte guarantee.

This test does not prove the production Linux host namespace race or Oracle
Cloud networking behavior. It did not test Pulumi or Chall-Manager integration,
and it did not verify public internet connectivity. Docker Desktop's Linux
engine is not the production VPS: the race between preflight and Docker's host
bind, manager volume permissions, Pulumi error wrapping, Ubuntu host firewall,
Oracle NSG/Security List, DNS, and public reachability remain unverified.
Review both the Ubuntu host firewall and Oracle NSG/Security List before
enabling the range in production. Do not open the range on the VPS based on
this implementation alone. This is not a production-readiness claim.

## VPS work still required

Before any public launch, review and configure both Ubuntu host firewall and
Oracle NSG/Security List rules for TCP `80`/`443`, the existing SSH port, and
the verified challenge port allocation range. Challenge gateway ports are
currently published on all host interfaces when `public_host` is set. Do not
expose the Docker API or Chall-Manager API. Direct challenge HTTP traffic does
not traverse Nginx, so the website TLS certificate does not protect these
connections. A dedicated challenge reverse proxy with HTTPS would be a
separate architecture change.

Uploaded Dockerfiles are untrusted build input, and the trusted manager/build
worker's Docker socket access is effectively host-level authority. Existing
container resource limits and network separation reduce risk but do not
eliminate kernel/runtime escape, build-time host compromise, CPU/disk
exhaustion, or denial-of-service risks on a single VPS.

## Disposable full-lifecycle test (2026-11-12)

A complete CTFd → Chall-Manager → Pulumi → target/gateway → janitor run was
executed on a disposable local Docker engine (amd64, Docker Desktop, 8 CPU /
7.2 GB) using Compose project `cyberdune-local`, its own database, Redis, state
volumes, registry and networks. CTFd was bound to `127.0.0.1:8001` only. The
scenario was built from `scenarios/web-container` and published to the local
registry as `localhost:5001/scenarios/web-container:v5-amd64`, digest
`sha256:0382a78036506c1aa515342f72d66777bd0889130846724a3c3a040e78073a1a`.

Observed results:

- Admin setup, login, user creation and challenge creation through the real
  admin web preset succeeded.
- First launch took 11.1 s; a second concurrent player launch took 11.5 s.
- Two players received different loopback ports (32768 and 32769) and
  different flags. A player submitting another player's flag was rejected;
  the owner's flag was accepted.
- Renewal succeeded without changing the port.
- Target containers were attached only to a per-instance internal network with
  no published ports, read-only root filesystem, all capabilities dropped,
  `no-new-privileges`, 128 MB memory and 0.5 CPU. Gateways were dual-homed on
  the internal target network plus a per-instance gateway network, read-only,
  all capabilities dropped, 32 MB / 0.25 CPU, and published only on
  `127.0.0.1`.
- A Chall-Manager restart did not destroy running instances; the gateway kept
  serving and the existing connection info stayed valid.
- With a 30 s challenge timeout, the janitor removed the instance and its
  networks about 30 s after expiry. The cached connection info returned the
  stale URL for roughly 60 s and then `data: None`. Relaunch after expiry
  succeeded on a new port (32771).
- Explicit destroy removed all instance containers and per-instance networks
  for both players.

This run validates the private-mode lifecycle on one Docker engine. It does
**not** validate public mode (the ledger and public binding path were not
exercised because `INSTANCE_PUBLIC_HOST` stayed empty), the ZIP/image builder,
malicious archives or symlinks, ARM64 native builds, worker reboot recovery,
TLS or edge routing, host firewall/NSG behavior, or capacity under load.

The release also fixes a version-tag mismatch: `scripts/configure-web-launcher.py`
accepted only `v2`–`v4` launcher references while the preset and
`publish-instance-launcher.sh` publish `v5`, and `publish-test-web.sh` still
tagged `v1`. The validator now accepts any numeric version and the publish
helper uses `v5`.

## Public-mode and ZIP results (2026-11-12)

The same disposable stack was then run with `INSTANCE_PUBLIC_HOST` set. Public
launches returned `http://<host>:<port>/` inside the configured range, the
gateway published only the reserved port, and the ledger tracked one `active`
lease per live instance. Stale `pending` leases and leases left by destroyed
instances were reclaimed on the next reservation after the allocator confirmed
no container or host listener owned the port. Destroy removes the gateway
immediately; the ledger entry is released lazily at the next reservation, not at
destroy time, because Pulumi does not run the scenario program during destroy.
The gateway route itself is the container, so a removed instance cannot keep
serving or capture another player's traffic.

A real defect was found: chall-manager runs the scenario program in Pulumi
preview when a challenge is created, so the port reservation executed as a side
effect and leaked a `pending` lease per challenge. The program now skips the
reservation when `req.Ctx.DryRun()` is true. Rebuilding and republishing the
scenario (`sha256:fc1c97c7e152eb7ff9c3f4868746333bd1881c6d464eae8257e531c162ca2120`)
confirmed that challenge creation no longer writes to the ledger.

The real ZIP builder (`services/instance-builder/worker.py`) was exercised
against the stack: path-traversal and symlink archives were rejected with 400, a
valid ZIP built and launched a challenge, and a ZIP with a failing `RUN` reported
`failed` while `finish` returned 409. This still ran on Docker Desktop, not the
dedicated worker, and no TLS edge was in front of it.
