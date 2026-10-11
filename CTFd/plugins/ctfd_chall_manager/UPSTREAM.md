Vendored from https://github.com/ctfer-io/ctfd-chall-manager
at commit `519faf40077274c61ced18213b88fad292c93154` (2026-10-11).
License: Apache-2.0, preserved in LICENCE. Runtime files only; upstream
development infrastructure and screenshots are not shipped.

CYBERDUNE changes:

- CTFd timing, pause, visibility, scheduled/module access and prerequisites
  apply to instance creation/read/renew; authenticated owners can clean up
  after an event. Non-instance IDs return 404.
- Resolve request timeouts at call time, including on first plugin load.
- Fetch current backend state for flag validation instead of cached state.
- Reject flags after the lease deadline, even before janitor cleanup.
- Do not log submitted flags or backend flag arrays at INFO level.
- Native browser controls retain CTFd's normal flag submission. No cross-account
  browser cache; connection information is rendered as text, not HTML.
- Instance controls use the existing CYBERDUNE styling.
- Invalid numeric startup settings fall back cleanly.
- Admin-only quick web creation uses the saved reusable scenario, generates a
  fresh flag seed per challenge and supplies private-instance/scoring defaults.
  The normal creation form and backend rollback path remain available.
- Admin ZIP uploads build through a private file queue on the Docker worker;
  CTFd gets no Docker socket. Automatic creation reuses the web scenario and
  supports build logs, failure recovery and idempotent registration.

Upgrades should compare these changes against the pinned upstream revision.
See docs/INSTANCES.md for installation, backend activation and validation limits.
