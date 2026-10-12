# CYBERDUNE production polish — 12 October 2026

CTFd version: **3.8.8**. The supplied **core-theme** and CYBERDUNE branding are retained.

## Issues found and fixed

- Nested challenge modal dialogs, forced 850px widths, excessive top margins, a backdrop simulated with a huge shadow, cramped metadata, and fixed button positioning broke small screens. Removed the offending rules and introduced shared responsive modal geometry.
- Buttons, inputs, spacing, focus, loading, disabled states and typography now use common tokens in `static/assets/integration.css`. The red/glass identity and chamfered challenge cards remain.
- Challenge cards have balanced grid spacing, safe long titles, consistent metadata and an explicit solved label. Removed the large solved GIF overlay that obscured text.
- Challenge detail styles are loaded once rather than injected for every modal. Description, metadata, files/hints, instance controls, submission and feedback have distinct spacing. Long URLs wrap; code blocks scroll horizontally inside their container.
- Flag submission has an accessible label, equal-height desktop controls, stacked mobile controls, an immediate loading state, a duplicate-submission guard, and readable transport errors. Existing CTFd validation/scoring still owns the result.
- Instance controls show checking/starting/ready/stopping/stopped/failed/expired states; mutations disable duplicate clicks, offer status recovery, and expose a copy button and countdown. Status polling is serial at five-second intervals while provisioning and stops on completion or modal closure. No automatic mutation retries.
- Profile-save positioning, duplicate form IDs, inaccessible team icon actions and unassociated floating labels are corrected. Tables retain their semantics inside responsive scrolling wrappers.
- Guest pages no longer open the authenticated notification event stream. Authenticated notifications remain enabled.
- The background animation was converted from a 22,444,863-byte GIF to a 2,508,370-byte VP9 WebM, retaining its visuals. It pauses for reduced motion and hidden tabs. The welcome effect runs once per tab and no longer blocks every home navigation for several seconds.

## Instance bottleneck and improvements

The VPS is ARM64; its original manager image, Pulumi CLI/provider and launcher were AMD64. Logs recorded a **106.072-second CreateInstance** with ordinary lookups taking milliseconds. CPU/RAM were not exhausted (about 10.7 GB available memory during inspection).

Built the **same manager v0.6.6**, with the version-matched Pulumi **3.237.0**, natively for ARM64. The official source release checksum was verified. Existing state/control networks are retained; a separate native plugin-cache volume prevents reuse of incompatible AMD64 provider binaries.

Measured real hidden probes:

| Operation | Before | Native manager | Native readiness-aware launcher |
| --- | --- | --- | --- |
| Launch | 106.072s in existing logs | 8.024s / 8.096s | 8.482s / 8.253s |
| Retrieve | Milliseconds | 0.005s | 0.005s |
| Stop | Not separately benchmarked | 4.129s / 4.141s | 4.117s / 4.077s |

All four probe targets returned **HTTP 200**, and their temporary challenges/instances were removed. These are measurements for the small Cookie Mirage fixture, not a promise that every uploaded application starts in eight seconds.

The v3 ARM64 launcher waits for the target to accept a TCP connection before reporting readiness. It is digest-pinned for new ZIP/image challenges. Existing challenges retain their pinned scenarios to avoid replacing active player containers; they still benefit from the native manager runtime.

The plugin now acquires mutation locks atomically, gives distributed locks a recovery expiry, and returns an existing instance on repeated launch requests. An absent instance is a normal `200`/null status rather than a repeated browser-facing 404. Added server-side creation timing without logging returned flags.

The upstream manager hardcodes a metrics exporter even with `OTEL_METRICS_EXPORTER=none`. The native build includes a small explicit `OTEL_SDK_DISABLED` opt-out, avoiding repeated calls to a nonexistent collector. Normal telemetry behavior remains available when that opt-out is unset.

## Files and backend changes

Main groups changed:

- `CTFd/themes/core-theme/templates/`: base/navigation, challenge board/detail, auth forms, settings, user/team tables and forms, content pages/home.
- `CTFd/themes/core-theme/static/assets/`: shared tokens/components, board/detail CSS, corrected inherited supplied styles, rebuilt JS assets/manifest.
- `CTFd/themes/core-theme/assets/js/index.js`, `assets/js/challenges.js`, `vite.config.js`, and `package-lock.json`.
- `CTFd/plugins/ctfd_chall_manager/api/instance.py`, `assets/view.html`, `assets/view.js`, `utils/instance_manager.py`, and `utils/lock.py`.
- `scenarios/web-container/main.go`, launcher publish/configuration scripts.
- `services/native-manager/`, `docker-compose.native.yml`, `scripts/build-native-manager.sh`.
- `tests/test_cyberdune_instances.py`.

**No CTFd core files, schema changes or flag/scoring algorithm changes.** No user/account, challenge-description, logo configuration or competition data was replaced.

The theme's supplied customized CSS differs from its SCSS source. Its base template explicitly retains that supplied stylesheet; Vite rebuilds do not empty the static directory. This avoids losing the visual identity when rebuilding JavaScript.

## Validation and remaining attention

- 13 automated backend/ZIP tests passed: owner/team isolation, correct/incorrect flags, timing/expiry, authorization, mana, lifecycle, safe ZIP extraction, offline worker/failure, ZIP finalization retries, duplicate launch and busy-lock rejection.
- Browser QA covers 320, 375, 430, 768, 1024, 1280 and 1440px; home, navigation, board, long-description/code/file/hint modal, settings/profile, notifications, scoreboard, content, auth and team pages. Separate tests exercise real CTFd registration, create/join team, submissions/solved state/scoreboard, and simulated instance launch/extend/restart/stop/copy/failure/recovery.
- Real private VPS instance build/provision/readiness/HTTP/cleanup probes passed. Frontend deployment is backed up under `~/cyberdune-theme-backups/polish-*`.
- Instance targets continue to use the existing private loopback/SSH access model. Public player access is a separate product change; this pass does not expose vulnerable targets to the internet.
- Future ARM64 deployments can build with `scripts/build-native-manager.sh` and append `docker-compose.native.yml` last in their existing Compose file list. Keep that override when recreating the manager so it does not revert to emulation.
- GitHub synchronization still needs the previously failed large push to be resolved; the live deployment uses the verified direct package transfer.
