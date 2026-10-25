# CTFd 3.8.9 upgrade

Upstream release: https://github.com/CTFd/CTFd/releases/tag/3.8.9

This integrates all four changes from the official 3.8.8 to 3.8.9 release:

- CTFd identifies itself as 3.8.9.
- certifi is pinned to 2026.10.19, removing the distrusted root certificate.
- Docker builds install the upstream pip 26.2.2 wheel with its SHA-256 verification.
- The old system pip is removed in both Docker stages, and the upstream changelog is included.

The project metadata, frozen uv lock and README also reflect 3.8.9. A direct certifi pin keeps uv installs aligned with the runtime requirements. Existing CyberDune UI, plugins, security fixes, database configuration and instance launcher are retained. This release adds no database migrations.

Deployment must use a freshly rebuilt image: changing the version string or restarting the previous image does not update the certificate bundles. Back up the database, uploads, signing key, source, effective Compose configuration and deployment wrapper first. Test startup and migrations against a disposable database copy and a separate Redis instance before replacing only the application container.

Use the existing production Compose wrapper and its instance/native-manager overlays. Preserve the signing secret volume, database and upload mounts. Verify the running CTFd, pip and certifi versions, absence of system pip, database counts, trusted-host rejection, public pages and unchanged theme assets. Keep the previous image and a rollback script; do not reset production data during application rollback. If needed, restore the prior `ctf_version` marker after reverting the application. Never restore a whole old database over new player activity merely to roll back this patch release.
