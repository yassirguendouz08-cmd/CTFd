# Optional challenge instances

CYBERDUNE now includes the Apache-2.0 CTFer.io `ctfd-chall-manager` plugin,
pinned to `519faf40077274c61ced18213b88fad292c93154`. Its `dynamic_iac` challenge
type gives players Launch / Renew / Restart / Destroy controls. In user mode,
ownership belongs to a user; in team mode, teammates use their team's instance.
Standard and dynamic-scoring challenges continue to work without an instance backend.
The upstream plugin is in public beta; keep the pinned version until an upgrade
has been tested. Local adjustments are recorded in the plugin's `UPSTREAM.md`.

## Install the platform update

In the existing Codespace or server checkout:

```bash
cd /workspaces/CTFd  # use your actual checkout path on a VPS
git fetch origin
git merge --no-ff --no-edit origin/master
docker compose up -d --build ctfd
```

This recreates the app container while retaining the existing database and upload
mounts. Back up the database before installing a new plugin: it adds its own table
and configuration keys. It does not convert or delete existing challenges/users/teams.
The default compose command does **not** start challenge containers or activate
Event Mode. The Instances navigation item stays hidden until backend activation.

Admin > Challenges > New now offers **dynamic_iac**. Admin > Plugins >
Chall-Manager > Settings shows the backend connection status. Instance challenge
creation requires a working backend and a real scenario; do not choose this type
for ordinary file/download challenges.

## Start a single-host backend for development

Requires a Linux Docker host. This workstation does not have Docker installed;
the backend overlay has not been exercised against a live Docker daemon here.
CTFd's existing MariaDB/Redis/uploads are retained by the following commands.

```bash
cp .env.instances.example .env.instances
openssl rand -hex 32
# Set CM_PULUMI_PASSPHRASE in .env.instances to the generated value.
docker compose --env-file .env.instances \
  -f docker-compose.yml -f docker-compose.instances.yml config --quiet
docker compose --env-file .env.instances \
  -f docker-compose.yml -f docker-compose.instances.yml up -d --build
```

The extra services are Chall-Manager v0.6.6, its janitor (expiry cleanup), and a
local scenario registry. Their state uses named volumes. Keep the passphrase and
those volumes in your backups. The manager API has **no public port mapping**;
only CTFd and the janitor reach it through the control network. The registry is
bound to `127.0.0.1:5001`. Only the manager receives the Docker socket, never CTFd
or a challenge container. Socket access gives it control of this Docker host.

For a public CTF with deliberately vulnerable targets, use a dedicated worker
host or a properly isolated Kubernetes deployment. The supplied single-host
overlay is a development starting point, not a claim of production isolation.
On a separate worker, connect CTFd to the manager over a private authenticated
tunnel; do not expose its unauthenticated API to the Internet. Configure the real
worker URL in the plugin settings. FRP is optional for this integration and is
not bundled; target routing depends on your scenario and domain setup.

In Admin > Plugins > Chall-Manager > Settings verify:

- API URL: `http://chall-manager:8080` for the supplied overlay.
- Mana total: `3` initially (each challenge can cost 1 or more).
- Connection status: reachable.

Startup environment defaults are written only on the first plugin installation.
Later URL/mana changes must be made in the admin settings, not just in Compose.
API calls default to a 60-second timeout on the supplied deployment.

## Add an instance challenge

An instance needs **both** a challenge image and a deployment scenario (an OCI
artifact containing a Pulumi program). An arbitrary Docker image alone is not
a scenario. Follow the upstream [Docker walkthrough](https://ctfer.io/docs/ctfd-chall-manager/introduction/getting-started/)
to build and publish the scenario, then adapt it for your actual challenge.
The walkthrough's example is a simple Docker launcher, not automatic unique-flag
injection or a hardened production deployment.

1. Build a real Docker challenge image. Set CPU, memory, process and network
   limits in its scenario; do not mount the host socket or platform data into targets.
2. Package and publish the scenario to the local registry (`localhost:5001` from
   the host). From the manager, the same registry is `scenario-registry:5000`.
   Use a versioned scenario reference, ideally pinned by digest.
3. Create a `dynamic_iac` challenge. Set the usual name/category/description and
   scoring values. For constant points, set Minimum equal to Initial.
4. Leave **Shared** disabled for a private instance per account. Set **Mana cost**
   to `1`, **Timeout** to `600` seconds and pool Min/Max to `0` initially. The janitor
   removes expired instances, and Renew extends the lease.
5. Set **Scenario** to your published artifact. Fill **Additional** with the
   values that scenario expects (such as image, internal port and worker hostname).
   The example Docker scenario returns a dynamically published port; configure
   worker firewall/routing for its real target ports. An HTTPS platform does not
   automatically make target endpoints HTTPS.
6. If you want account-specific flags, the scenario must inject the generated
   `FLAG` into the image and export it through the SDK's `Flags` output. The image
   must actually use that value. See the [flag guide](https://ctfer.io/docs/ctfd-chall-manager/learn-more/flag/).
   Leave CTFd's static flag list empty for that challenge to avoid a common fallback.
7. Test with two accounts (or two teams): launch, compare endpoints and flags,
   submit your own flag, reject the other's flag, renew, restart and destroy.
   Confirm expiration cleanup and confirm that ordinary challenges still work.
   Publish the challenge only after that check.

The player API derives ownership from the login session, never a caller-supplied
sourceId, and omits flags and admin-only scenario/configuration fields from
player responses. Current backend state is checked during submission. Unique
flags reduce flag sharing; they do not prevent sharing the solution method.

## Stop the optional backend

Destroy running instances from the admin monitor first; stopping the manager
does not destroy target containers. Then stop only the extra services:

```bash
docker compose --env-file .env.instances \
  -f docker-compose.yml -f docker-compose.instances.yml \
  stop chall-manager-janitor chall-manager scenario-registry
docker compose up -d ctfd
```

Do not run `down -v`: database and instance state must be retained. Keep the
plugin installed if the database contains `dynamic_iac` challenges. Exporting
CTFd alone does not back up manager state, scenario artifacts or Docker images.

## Verification performed

The existing platform/authentication/team/scoring regression suite passes with
the plugin loaded. `python -m unittest tests.test_cyberdune_instances -v` checks
instance lifecycle, server-derived account/team ownership, cross-account flag
rejection, expired-instance rejection even with cached state or before janitor
cleanup, mana limits, timing/access rules, admin/type integration and ordinary
flags during backend failure. Desktop/mobile browser checks also exercised the
controls and the theme's normal flag submission without JavaScript errors. These tests
use a fake HTTP backend; real container launch, DNS, TLS and worker firewall
validation remain deployment checks on your Linux host.
