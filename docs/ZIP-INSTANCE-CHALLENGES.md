# Create an instance challenge from a ZIP

Open **Admin → Challenges → New Challenge → Upload instance ZIP**.
Choose your ZIP, enter a name, category, description and points, then click
**Build and create challenge**. The name can default to the ZIP filename.

Keep the progress page open. It shows the build log and opens the new challenge
automatically when the image is built and registered. The challenge starts hidden;
preview it, then make it visible using the usual challenge editor. Recent uploads
remain accessible from the upload page if you close a build tab. A failed backend
registration can be retried without rebuilding or duplicating the challenge.

The ZIP must contain exactly one `Dockerfile` and its application files, either
at the root or inside a single challenge folder. Maximum upload size is 50 MB,
unpacked size 250 MB, and 2000 entries. Path traversal, symlinks, duplicate paths
and encrypted entries are rejected. Docker Compose projects and archives without
a Dockerfile are not supported by this launcher.

The app reads its per-instance flag from the `FLAG` environment variable. Its
port is detected from the first numeric `EXPOSE` declaration, otherwise 8080;
you can override it under Advanced. The existing launcher supplies private
instances, a fresh challenge seed, 10-minute leases and fixed points. The app
must support the launcher's read-only filesystem and existing target access
configuration. Targets still use the existing VPS loopback/SSH connection flow.

Install the builder once on the same Linux Docker worker:

```bash
sudo bash scripts/install-instance-builder.sh
bash scripts/publish-instance-launcher.sh
sudo docker compose restart ctfd
```

The `cyberdune-instance-builder` systemd service reads a private file queue under
`.data/CTFd/uploads/instance-builds`. CTFd receives no Docker socket and the worker
exposes no network API. Only authenticated admins with a valid CSRF nonce can
submit builds or register the completed challenge. The host worker uses Docker
to build administrator-provided Dockerfiles, one at a time, with a 15-minute
limit and 10 MB log limit. Uploaded sources and bounded logs are retained in the
private queue; extracted build contexts are removed after a build. The generated
images live in the worker's Docker daemon, shared with the existing manager.
The one-time publication helper saves the digest-pinned v2 launcher for future
uploads. A dedicated, restricted TCP gateway publishes a random loopback port
for each target; the target itself remains on its private internal network.
IP forwarding is disabled in the gateway. Docker's actual port binding is
inspected before connection information is returned. The Compose init
service creates the file-backed Pulumi state directory before the manager starts.

Service status and operational logs:

```bash
sudo systemctl status cyberdune-instance-builder
sudo journalctl -u cyberdune-instance-builder -n 50
```
