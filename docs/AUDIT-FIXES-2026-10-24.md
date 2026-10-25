# Audit fixes and deployment — 24 October 2026

The audit report remains a record of the original findings. This document describes the resulting code changes and the deployment checks needed to activate them.

## Application changes

- Instance access validates one challenge ID, rejects conflicting query/body IDs, and passes the authorized ID directly to the operation. Hidden/locked, scheduled, prerequisite and module restrictions apply to that exact challenge. Player ownership remains session-derived.
- Manager listing errors, malformed stream records and ownership mismatches block new allocations instead of becoming zero usage.
- Instance challenge scheduling normalizes ISO 8601 dates to UTC. Required scenario/configuration fields are validated before database writes.
- The challenge board exits loading after errors, offers Retry/login, preserves cards during failed refreshes, and displays challenge-opening errors. Search and solved/unsolved filters work together with categories and translations.
- Flask/Werkzeug, Flask-SQLAlchemy, Flask-Migrate and Flask-Babel were updated together. The existing SQLAlchemy 1.4 and Marshmallow 2 schemas are retained; no application table migration is introduced by these fixes. Legacy Flask-Script was unused and removed.
- Requests are capped at 64 MB, authentication bodies at 64 KB, multipart form memory at 512 KB, and multipart parts at 200. The first two limits are independently configurable with `MAX_CONTENT_LENGTH` and `AUTH_MAX_CONTENT_LENGTH`. Align any host-side proxy limits with the application.
- New signing keys are private files; inability to persist a key fails startup. Compose stores its key in a persistent `signing_secrets` volume, preserving an existing source `.ctfd_secret_key` on first initialization. Keep an existing environment `SECRET_KEY` unchanged when upgrading.
- Compose publishes CTFd only on `127.0.0.1:8000`. The bundled proxy overwrites forwarding headers. Account emails use `PUBLIC_ORIGIN` when configured, and session-dependent responses vary on Cookie; authenticated pages are private/no-store.
- Shared-IP registration/login limits accommodate a workshop while retaining per-account/email limits. Configure `SECURITY_REGISTER_IP_MINUTE`, `SECURITY_REGISTER_IP_HOUR`, `SECURITY_LOGIN_IP_MINUTE`, and `SECURITY_LOGIN_IP_WINDOW` to match attendance; Redis outages continue to block protected writes.
- Long reading pages have a darker surface. CI now builds the deployed theme and tests its error recovery and filters.
- The builder removes finished queue jobs older than seven days and checks free disk before building. `--retention-days` changes the retention window. Images used by challenges are retained; there is no automatic global Docker prune.

## Deploy the application

1. Export CTFd from the admin backup interface and save a database/uploads backup. Record the currently deployed image and Git revision for rollback. Preserve any current secret instead of generating a replacement.
2. Review `.env.production.example`; set `PUBLIC_ORIGIN` and `TRUSTED_HOSTS` for the actual public hostname in a private `.env`. If the server already uses an environment signing key, keep that exact key in its existing secret mechanism. Do not print or commit it.
3. On the deployment host, validate `docker compose config --quiet`, then rebuild with `docker compose up -d --build`. With the optional instance backend, use the same Compose overlays and `.env.instances` as the existing deployment. Keep all existing volumes.
4. The Compose Nginx config is updated in this repository. If the VPS uses host Nginx, mirror the body limits, IP normalization and backend loopback binding there, then run `nginx -t` before reloading. Preserve the actual TLS configuration. Set proxy trust to the actual hop count; do not expose the app listener directly.
5. Test login, teams, hints, ordinary flag submission, and instance lifecycle with organizer-controlled test accounts. Verify that existing sessions and confirmation/reset links still work across an application restart.
6. Reinstall/restart the builder using the existing systemd installer to pick up retention changes. Retained queue jobs are temporary build history; the database and challenge images remain the authoritative challenge records.

These changes are in the local checkout. VPS deployment and real SMTP delivery must be verified using the actual server access and provider credentials.

## Public instance endpoints

The v4 launcher supports an explicit `public_host` for a dedicated challenge worker. New ZIP/image presets copy `INSTANCE_PUBLIC_HOST` into that field. Without it, bindings remain on loopback and show SSH instructions.

1. Point a separate challenge hostname at the worker. Configure its firewall for the Docker-assigned gateway ports, with the manager API, database, cache and Docker socket kept private. Do not use the platform's hostname for deliberately vulnerable targets.
2. Set `INSTANCE_PUBLIC_HOST` in the worker/CTFd deployment, then rebuild/publish the scenario with `scripts/publish-instance-launcher.sh`. The publisher runs the Go tests and configures the digest-pinned v4 artifact.
3. Existing challenges retain their current scenario/additional fields. Migrate them explicitly in the admin interface only after testing; the preset environment affects future creations.
4. Test from a different machine with two teams: distinct endpoints/flags, rejection of the other team's flag, renew, restart, destroy and expiration. The built-in direct gateway returns an HTTP endpoint. Use a separate TLS ingress if HTTPS target URLs are required; the platform's TLS does not secure a target's random port.

No public port is enabled automatically by an application update. DNS, firewall and real container readiness must be checked on the actual worker before publishing an instance challenge.

## Email, recovery and monitoring

- Use the existing account-security guide to configure the SMTP provider privately. Test real signup, confirmation, password recovery and delivery failures with organizer-owned addresses before enabling required email verification. Admin MFA can be supplied by an identity provider; an MFA provider has not been chosen automatically.
- Back up the database and uploads, the signing secret, the private environment/provider configuration, and the manager's state, Pulumi passphrase, registry and challenge images. Store backups outside the worker with restricted access. Restore them to a separate staging host and verify a login, a solve and an instance lifecycle before relying on the backup procedure.
- `scripts/check-platform-health.py` is a read-only probe with nonzero exit status on failure. Monitor it using the host's chosen alerting system, and alert separately on 5xx spikes, Redis/manager failures, build failures and low disk. No recurring automation or external notifications are created by this change.
- Public account directory visibility is retained. Choose the intended privacy settings through the admin interface. A CSP rollout should use report-only first and account for inline scripts/Alpine; this patch does not install a policy that would break the theme.

## Rollback

Restore the previous application image/source and dependency lock together. Retain the database, uploads, `signing_secrets` volume and existing instance volumes. Do not run `docker compose down -v`. A key copied into the persistent volume must remain the same key used before the upgrade. A scenario rollback requires selecting its previous digest; it is separate from rolling back CTFd.
