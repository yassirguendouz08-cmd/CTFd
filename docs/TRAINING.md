# CyberDune Training

`/training` is a separate, individual practice library. `/training/scoreboard`
ranks users by the number of published exercises they have solved. Equal counts
share the same rank. XP is an independent learning reward, never a tie-breaker.
CTF challenges, submissions, teams, awards and scores are unaffected.

## Current checkpoint

- 18 original starter exercises: nine downloadable challenges and nine sandboxed
  browser simulations across nine categories.
- Three original Hard exercises: RSA CRT fault recovery, reversible 64-bit VM,
  and clock correlation plus GF(257) quorum recovery. Tests recover flags from
  player artifacts independently of the generators.
- Two adapted official picoCTF MIT examples: ECB 1 (Easy) and SQL Injection 1
  (Medium). Source: picoCTF/picoCTF at
  `457347a54f20f634733c69457afe0503b69021e1`; Tim Becker / ForAllSecure;
  Carnegie Mellon University copyright. License accompanies every download.
  Difficulty is locally estimated, not an official Academy rating.
- The supplied Bootcamp export imports 45 exercises into Training only. 21
  reviewed offline exercises publish; 24 remain unpublished pending restoration
  of isolated services, missing artifacts or event dependencies. Historical
  endpoints are removed from pending briefs. Admin review notes explain why.
  Nested ZIP organizer writeups, solvers, clear flag.txt, README/hint files and
  deployment scripts are withheld from player downloads. Original evidence is
  retained separately. Imported exercises retain their original shared flags.
- Direct links lead to the official CyLab Academy library/Primer. Academy solves
  do not affect local ranks. The restricted Academy library is not mirrored.

Generated exercises have per-user flags derived from the persistent application
signing key. Keep that key backed up. Public source contains no imported flags,
exported users, passwords, tokens, tracking data or private attachments.

## Administration

Open Plugins → Training (`/admin/training`) to create, edit, publish or unpublish
content. Static flag replacements clear additional imported accepted flags.
External labs require a separately hosted HTTP(S) URL. Browser starter labs are
simulations, not native shells or containers. Do not expose vulnerable services
inside the scoring application's process/network.

The SQL example is a bounded exception: each request opens a disposable `:memory:`
SQLite connection with one fictional user. An authorizer permits only SELECT and
reads of that table, extensions are disabled, database is query-only, and query
length/execution are bounded. It has no access to CTFd's database or credentials.

Import the supplied private export inside the running application context:

    flask training import-bootcamp /private/path/bootcamp.zip

Import is idempotent by source slug and never overwrites existing edits. It reads
only challenges/flags/files/hints. Never use CTFd's full restore to import this
pack. Export paths, compression limits and nested archives are validated before
mutation; source code/binaries are never executed by the importer. Player files
use separate TrainingAttachment records, so generic CTF `/files/...` cannot serve
them. All downloads require a verified authenticated account when configured.

Five additive plugin tables hold challenges, solves, attempts, accepted hashes and
attachments. Unpublishing preserves solves; only published tasks count toward the
current rank. Foreign keys cascade account deletion. Flags are keyed hashes;
submitted guesses are never saved. POST requires session CSRF even with an
Authorization header. Submit limit: 30 attempts per user per minute; concurrent
correct submissions are deduplicated by a database uniqueness constraint.

    flask training prune-attempts --days 30

The maintenance command removes old attempt telemetry while retaining solves.

## Deployment and rollback

Back up MariaDB, uploads and signing secrets before enabling the plugin. Rehearse
startup and the content import against a disposable restored database. Keep both
DB and uploads in future backups. Application rollback must preserve the new
Training tables and uploads; do not restore an old database over player progress.
The new plugin directory must be removed from the bind-mounted source tree when
rolling back to an image without this plugin. No existing CTF tables are migrated.
