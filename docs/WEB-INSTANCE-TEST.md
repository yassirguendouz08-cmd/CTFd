# Cookie Mirage and the reusable web launcher

The backend setup is performed once. Future compatible web challenges reuse
`scenarios/web-container`; create a folder under `challenges/` with a Dockerfile,
then run `bash scripts/publish-test-web.sh folder-name` on the Docker worker.
Each image must listen on port 8080, read its flag from `FLAG`, run as a non-root
user, and work with a read-only filesystem. Other ports can be set in Additional.
No Docker socket or platform files are mounted into targets.

This is a private, single-host development test. Targets use a separate internal
Docker network, 128 MB memory, half a CPU, dropped capabilities and no new
privileges. The nproc ulimit is a per-user limit, not a Docker cgroup PID limit.
Use a dedicated worker with stronger isolation and target routing for public CTFs.
The Python stdlib server is for this small training example, not a production app.

## First publication on the existing Oracle VPS

Run inside the Ubuntu SSH session (not Windows PowerShell or the Codespace):

```bash
cd ~/CTFd
git pull --ff-only origin master
bash scripts/publish-test-web.sh cookie-mirage
```

Requires the running scenario registry on localhost:5001, Docker/BuildKit,
OpenSSL, curl, and network access to the pinned Go modules and build images.
The helper builds the app for the worker's native CPU and the Pulumi binary for
AMD64, matching the manager running under QEMU on this ARM64 Oracle VPS.
If using a native ARM64 manager later, set `SCENARIO_ARCH=arm64` when publishing.
The scenario artifact contains a compiled executable and Pulumi.yaml; it is not
the challenge Docker image. Publishing follows the
[upstream scenario format](https://ctfer.io/docs/ctfd-chall-manager/introduction/getting-started/)
and [ORAS push](https://oras.land/docs/commands/oras_push/).

The helper prints a digest-pinned Scenario address and three Additional rows.
It keeps a random seed outside Git in `~/.config/cyberdune/challenges/NAME.seed`.
Back up that directory securely. Do not share seeds with players or regenerate
them while active instances exist. Flags are deterministic HMACs of the manager's
instance identity and the challenge seed; the SDK exports them to the backend.

## Create the challenge in CTFd

For the simple admin workflow, open **Plugins → Chall-Manager → Settings →
New web challenge**, enter a name and the Docker image, then click Create.
It generates a new flag seed and fills the scenario, private sharing, 10-minute
timeout, mana and constant points automatically. Description/points/port are
optional. The first test image is `cyberdune/cookie-mirage:v1`.
The installed default launcher is `scenario-registry:5000/scenarios/web-container:v1-amd64`.
You can save a digest-pinned reference once in the **Web scenario** setting;
all subsequent quick creations use it. Image content still needs to be built
or made available on the worker once per new app; the admin form cannot create
a new application from only its name. No terminal command is needed to reuse
an existing image or to launch players' instances.

For other scenario types, the complete dynamic_iac form is still available:

- Type: dynamic_iac; Name: Cookie Mirage; Category: Web.
- Description: The portal trusts your browser a little too much. Can you reach the admin page?
- Initial and Minimum: 100; Linear Decay: 10.
- Sharing: Disabled; Destroy on flag: Disabled; Mana Cost: 1.
- Until: empty; Timeout: **600** (seconds; the plugin adds the unit for the API).
- Scenario: copy the exact digest-pinned address printed by the helper.
- Advanced: add `image`, `port`, `flag_seed` with the printed values; click **Apply**.
- Pool Min and Max: 0. Create it, keep it Hidden and leave static flags empty.

The instance controls are gated by normal CTFd visibility/timing rules; use an
admin preview or make it visible only during your private test. Do not add a
common static flag. The backend checks the current account/team instance flag.

## Open the private instance

Launch from the challenge. Its connection information includes the dynamic VPS
port, for example 32771. In a **new Windows PowerShell** terminal, replace 32771
with the actual port shown for your instance:

```powershell
ssh -i "C:\Users\guend\Downloads\ssh-key-2026-10-11.key" -N -L 18080:127.0.0.1:32771 ubuntu@51.170.136.188
```

Keep that terminal open and visit http://127.0.0.1:18080 in your browser.
The target endpoint is HTTP inside the encrypted SSH tunnel. A loopback URL
without the tunnel points to your Windows computer, not the VPS.

Test with two accounts: different endpoints and flags, own flag accepted,
other account's flag rejected, Renew/Restart/Destroy and 10-minute expiry.
QEMU/Pulumi startup may take longer than the plugin's current 60-second timeout;
inspect manager logs and confirm the operation before retrying failed launches.

## Organizer solution

The homepage sets `role=guest`. Edit that cookie to `role=admin`, then visit
`/admin`. Only that instance's injected flag is shown. `/robots.txt` hints at
the admin route. This intentionally insecure authorization is contained in the
challenge app, never the platform authentication.

## Updates and power cycles

Use `~/ctfd-instances` for Compose changes once the backend is enabled, so CTFd
retains the instance-control network. `~/ctfd-compose` does not include it.
The production host Nginx remains in charge of 80/443; do not start Compose's
nginx service. Keep all existing database credentials, named volumes and the
Pulumi passphrase. Destroy test instances before switching off the VPS.
After a power cycle, verify AMD64 emulation still works and all services are Up.
The backend images use unless-stopped and the platform uses its existing policy.
Real Docker launch/cleanup and power-cycle behavior must be checked on the VPS;
this workstation has no Docker daemon.
