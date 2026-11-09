# CyberDune CTF Platform — Project History and AI Handoff

This document gives a continuing AI agent the project context and the work completed so far. Read it together with the current source code and the live GitHub `master` branch. It is a project brief, not permission to make unrelated changes. Never expose credentials, private keys, database secrets, or production user data in prompts, logs, or commits.

## Project and owner preferences

- Repository: `yassirguendouz08-cmd/CTFd`
- Local checkout: this `platform/` directory inside the CyberDune workspace
- Production website: <https://ctf.cyberdune.online>
- The product is a CTFd-based cybersecurity training and CTF platform with a custom Academy plugin.
- The owner usually gives instructions in Moroccan Darija. Keep replies natural and concise in Darija when appropriate.
- User-facing site content should use clear standard English and follow the site language selector for supported translations. Do not put Darija, unnecessary source-platform branding, or internal implementation terminology in challenge descriptions and page headings.
- Keep the Academy typography, colors, challenge cards, and opened challenge detail view consistent with the existing CTF pages.
- Keep Academy scores and progress separate from the regular CTF/team scoreboard. Academy uses flags and ranks by challenges solved; points can appear on cards, but Academy must not use XP.

## Work from the initial platform review

The owner first asked for a broad review of platform bugs, vulnerabilities, and broken functionality, then asked to fix the problems found. The site and project were subsequently inspected and changes were made over several rounds. Do not invent a precise list of original audit findings that is not present in the current code or commit history; inspect the relevant commits and code before reporting detailed vulnerability claims.

The owner also asked to update CTFd after a newer version became available. CTFd was upgraded to **3.8.9** in the [security-release commit](https://github.com/yassirguendouz08-cmd/CTFd/commit/3eede348), including the upstream 3.8.8→3.8.9 security patch, dependency/tooling updates, and project metadata. That release was validated with 67 focused Python tests, a fresh ARM64 image, and startup against a restored disposable MariaDB copy with Redis; the signing key, schema and player counts were checked during deployment.

UI requests in the earlier work included removing the pause-animation control, aligning site styling, and estimating concurrent-user capacity. Capacity was discussed as an estimate; do not call it a measured load-test result unless a benchmark exists.

### Earlier platform work recorded in GitHub history

- **Platform foundation and theme (Oct 11–13):** integrated the supplied CyberDune theme and aligned the CTF platform with the CyberDune club site; refined the public homepage, typography, motion, logo, favicon and footer; made team creation/join screens responsive; kept English/French/Arabic language choices; added search metadata, sitemap and crawler discovery.
- **Instances and challenge operations (Oct 11–12):** added optional per-account challenge instances, ZIP-based instance challenge creation, explicit dynamic port mapping, isolated target gateways, and controls/terminal support for the Oracle VPS. Follow-up work handled emulated-instance requests, stale Codespaces routes/firewall rules, proxy setup, and instance provisioning/presentation.
- **Security and account flows (Oct 12–15, then Oct 25):** hardened verification and account flows with shared rate limits; improved instance authorization, quotas, scheduling, request-size limits, trusted-proxy handling and signing-key persistence; clarified admin access/role updates; protected hidden challenge attachments; and added regression coverage. See [platform hardening](https://github.com/yassirguendouz08-cmd/CTFd/commit/05fb014d44d5ae18af13900e6b2e6a2c5826b316).
- **Rules and starter content (Oct 15–17):** added editable CTF rules, private beginner/bootcamp exercises, safe admin flag previews, challenge localization, OSINT/sanity challenges, and author credits.
- **Footer motion control:** removed the pause/animate button while retaining the language selector and reduced-motion behavior. The [footer change](https://github.com/yassirguendouz08-cmd/CTFd/commit/1825ee4c) was verified on the live home, login, scoreboard and rules pages.
- **Academy work (Oct 29):** started with an independent training library and reviewed challenge packs; then refined the modal, card style and points/solve counts, removed promotional guide links, renamed it Academy, changed the board to rank by captured flags, removed Bytecode stepper, and finally replaced all browser labs with downloadable files. See the Academy commits listed below.

The user also shared a disk image and asked how to recover a flag from it; that was challenge-solving help, not a change to the platform codebase.

## Academy — goals and delivered behavior

- Added a standalone practice area presented as **Academy**, with a challenge library, challenge details, downloads, flag submissions, progress, and a separate scoreboard.
- Academy challenges do not affect CTF/team score, CTF solves, or the main scoreboard. Its ranking is by flags/challenges solved. Academy is flag-based; it is not an XP system.
- Academy cards were restyled to match CTF challenge cards, including displayed solve counts and points. The detail view and typography were aligned with the rest of the site.
- Removed the extra challenge-page guide/practice promotion panel as requested. The user asked for challenge cards to behave like regular CTF cards, with the opened challenge details presented in the same general style.
- Challenge text is in clear English, with translations controlled by the site's language setting. Avoid adding source-site names to visible titles; keep titles short and site-appropriate.
- The plugin includes admin controls for creating/editing exercises, flags, points, difficulty, publication, and external resource URLs. Standalone external labs are admin-managed; the built-in exercises are downloadable artifacts.

## Academy content and browser-lab replacement

- The user supplied a CTF Bootcamp ZIP and asked to reuse appropriate existing challenges, plus use picoCTF/picoGym as a learning source across Easy, Medium, and Hard levels.
- The user wanted some genuinely difficult challenges. Build challenging, well-tested exercises, but do not claim any challenge is impossible for all AI systems; verify solvability and avoid relying on obscurity.
- The nine built-in browser labs were permanently removed, including Bytecode stepper. The related challenge rows and solve/attempt/answer/attachment records were deleted in a backed-up production migration.
- The interactive SQL exercise was changed to an offline, downloadable sample; it no longer runs a browser lab or calls the platform database.
- Added eleven downloadable replacement challenges across Web, Cryptography, Forensics, OSINT, Reverse Engineering, Pwn, Linux, Networking, and Misc, with Easy/Medium/Hard difficulty. Their titles include Response Header Trace, Rotated Dispatch, Event Correlation, The Archived Route, Bytecode Trace, Stack Snapshot, Hidden Backup, Fragment Courier, Signal Filter, XOR Postcard, and Proxy Chain.
- Artifact generation and flag recovery were checked for all eleven replacements; the offline SQL exercise was also checked. Challenge flags are generated per user for built-in artifact challenges.

## Previously deployed releases

- GitHub commit `1b988f2a78cbe186e80e280f9a66711431bd1391` (`Serialize Academy cleanup across workers`) was the known head before the current visibility-control work.
- Earlier Academy replacement commit: `ea87709fe40760162c162baea17152f8ca719eec` (`Replace Academy browser labs with file challenges`).
- Production Academy was checked at <https://ctf.cyberdune.online/academy>; the CTFd health endpoint and Academy page returned successfully after the replacement release.
- The backed-up production release is under `/home/ubuntu/cyberdune-release-backups/academy-browser-labs-20261029T212932Z`. It contains a compressed full database backup, plugin backup, Academy-table-only backup, and deployment records. Keep it private.
- Python compilation, JavaScript syntax, `git diff --check`, and challenge-artifact checks passed in earlier work. Local unit tests have not run because `pytest` is unavailable (`No module named pytest`).

## Academy admin hide/show switch — completed

The owner asked for an admin-panel button to hide the entire Academy when desired and show it again later. The feature is on GitHub and deployed:

- `CTFd/plugins/cyberdune_training/__init__.py` adds a persistent visibility setting and gates `/academy`, `/training`, scoreboard, challenge, download, attachment, and submission routes while hidden. It also removes the Academy entry from the public navigation and restores it when shown. The admin route remains available to admins. The value is read directly from the database per request so multiple Gunicorn workers do not keep stale memoized state; both textual `false` and CTFd's stored `0` are interpreted as hidden.
- `CTFd/plugins/cyberdune_training/templates/training/admin.html` adds the current visibility status and a “Hide Academy” / “Show Academy” button.
- `tests/test_cyberdune_training.py` adds a hide/restore test for the library, scoreboard, challenge details, and downloads.
- Latest known GitHub head: `5eff4f50d27ea02a3d70534ad6efdc984005a8dd`.
- Before deployment, the VPS saved the changed plugin files under `/home/ubuntu/cyberdune-release-backups/academy-visibility-navigation-v2-20261029/plugin-before.tar.gz`.
- Live smoke checks confirmed the library, both scoreboard routes, a challenge page, and its download route returned 404 while hidden; the public homepage no longer showed Academy in navigation. The library, legacy library route, and scoreboard returned 200 after restoring visibility, and Academy reappeared in the homepage navigation. The temporary setting was removed afterward, leaving Academy visible by default.
- Local Python compilation and targeted `git diff --check` passed. The pytest command was attempted but could not start because pytest is not installed.

## Git and deployment cautions

- The local Git checkout has many pre-existing modifications and its branch diverges from the current remote. Never run broad `git add`, commit unrelated working-tree files, reset, or ordinary push.
- GitHub updates in this project were made against the verified live `master` head through the connected GitHub app. Continue to fetch current remote file content and expected blob/head before updates; use a compare-and-swap update.
- Deploy only the intended plugin files after review and retain a rollback snapshot. The hide/show feature does not need a schema migration and must not alter challenge records, solves, users, or CTF scores.
- The production setting is visible by default if absent. Leave Academy visible after smoke testing unless the owner explicitly changes that setting.
- Do not include SSH private-key material or deployment secrets in this file. Credentials remain in the owner's environment.
