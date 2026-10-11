# CyberDune redesign verification

Verified on 11 October 2026 against CTFd **3.8.8**, in a local fixture-only Flask
application with an in-memory SQLite database. Real Codespace MariaDB, Redis,
accounts, uploads and configuration were not modified.

## Design provenance

Actual Google Stitch MCP calls generated twelve references: landing and two
alternatives; challenge board and a refined variant; login, registration, recovery;
scoreboard, profile, event information; mobile landing. The generated landing was
retrieved independently with get_screen. See [Stitch records](stitch/README.md) for
project/screen IDs and original PNG/HTML exports.

The running theme is Jinja/Alpine/CTFd. Synthetic prototype policies and metrics
were not transferred. Layouts were adapted to original forms and authorized data.

## Completed checks

- All custom Jinja templates compile in the actual CTFd application.
- Homepage, authentication, content, challenges, members and standings render;
  custom assets and compiled core fallback resolve.
- Registration/login/logout, settings, notifications, attachments, free hints,
  incorrect/correct flags, solved state and score changes pass.
- A dynamic-scoring plugin challenge renders and accepts its flag.
- Team enrollment, creation, joining and private/public team pages pass.
- Theme activation backs up configuration; rollback restores prior theme/CSS.
- Homepage rendering disables metrics requests for hidden scores and admin-only
  challenges; original API visibility restrictions remain intact.
- Browser checks confirm homepage figures and top-three preview match actual
  authorized fixture API responses. An unset schedule shows no countdown.
- Category deep links select the correct filter after asynchronous board loading.
- Scoreboard search preserves numeric ranks and shows a genuine no-match state.
- Password visibility and recovery email form/nonce work.
- Real browser registration, login, filters, modal/files, charts, profiles and
  logout pass without theme JavaScript runtime errors.
- 390px, 768px and 1440px checks cover navigation, forms, dialogs, challenge cards,
  standings, profiles and content without viewport overflow.
- English/French/Arabic pages, Arabic RTL, translated empty states and actual
  language switching pass; navbar/settings expose exactly en/fr/ar.
- Admin challenges/config/users and original mobile navigation pass with scoped
  appearance and no runtime errors; controls, editors and scripts stay upstream.
- Representative final desktop/mobile/Arabic screenshots were visually reviewed.

The new enhancement uses one decorative SVG network behind the existing hero,
two signal paths, two sparse pulses and a scan line. Typing completes once; there
is no continuous JavaScript animation loop, synthetic telemetry or extra API
polling. Motion pauses while the page is hidden and honors reduced motion. A
persisted pause/resume control stops decorative CSS motion. Earlier desert art
and large terminal panels remain unused. Reduced-motion CSS disables transitions. Fonts are locally served
with OFL licenses. Expected anonymous /events HTTP 403 requests are permitted by
the browser suite; no other unexpected failed requests were found.

## Live rollout still required

After your PC push, run bash scripts/update-cyberdune.sh in Codespaces, then refresh
forwarded port 80 with Ctrl+Shift+R. Check configured dates, challenge access,
standings visibility, team mode, logo and an authorized test submission.

Local QA uses SQLite rather than live MariaDB/Redis. Email delivery, OAuth,
external challenge instances and every plugin/bracket/freeze setup were not tested
against live services. Keep core/admin themes and verify event integrations. For
upgrades, compare upstream templates and API contracts; see [THEME.md](THEME.md).

## Advanced operations enhancement — local QA

- Existing browser suite: registration/login/logout, filters, challenge dialogs,
  attachments, charts, profiles, mobile navigation and no unexpected errors.
- English, French, Arabic and RTL checks pass after the enhancement.
- Motion checks: one-pass typing, pause/resume persistence, reduced-motion static
  rendering, mobile width, finite real-score update highlight and cleanup.
  The observer test changes only fixture DOM text, never backend points.
- Desktop hero, mobile hero, challenge board, modal and standings screenshots
  reviewed. Existing backend, scoring, flag validation and databases are untouched.
- CSS and SVG assets are local; existing Font Awesome category icons require no
  new dependency. Effects have no canvas, video, filters or oversized blur layers.

## Professional refinement

The operations enhancement above is a historical checkpoint. The current theme
removes its decorative network SVG, typing cursor, motion toggle, HUD corners and
redundant labels. Card, metadata, form and footer typography is more readable;
real score/solve change feedback remains finite and honors reduced motion.
Current screenshots replace the preceding animated design previews.

## Centered landing

Removed the entire Mission briefing from the homepage, including start/end dates,
schedule badge, format panel and countdown. The headline, copy and actions are
centered; decorative accent colors are neutralized while primary buttons and the
official logo retain the red brand accent. Competition scheduling still works in
CTFd and is not changed by this presentation-only adjustment. English/French/Arabic,
RTL/mobile rendering, real homepage metrics, category links and standings search
pass. Current desktop/mobile screenshots were reviewed.


## Platform development mode — 2026-10-11

Validated against isolated in-memory CTFd fixtures; no deployed database was
accessed or changed.

- Default mode suppresses dates/status/countdown even with configured timing
  values and an old stored index-page announcement.
- Explicit Event Mode displays configured name, escaped briefing, UTC/local
  dates, and upcoming/live/ended status. Invalid/incomplete schedules fail closed.
- Browser countdowns target Start for upcoming events and End for live events;
  ended events have no countdown. Event CTAs adapt to the current status.
- Admin Config renders the mode/briefing fields. The backed-up platform helper
  clears only theme mode/start/end/freeze; fixture users, teams, challenges,
  solves and pages are unchanged.
- Existing integration verification passes registration, login/logout, profiles,
  notifications, user/team pages, team creation/join, challenge lists, files,
  hints, correct/incorrect flags, solved states, scores, dynamic scoring, admin
  APIs and theme configuration backup/restore.
- Browser checks pass at widths 320, 390, 768 and 1440 pixels: no horizontal
  overflow, working mobile navigation, authorized categories load, and no
  JavaScript errors across homepage and related pages.
- Focused unit checks cover absent/malformed settings, sample dates, incomplete
  schedules, missing names, and exact start/end status boundaries.

Activation and deployed-date cleanup: [Platform Mode guide](PLATFORM-MODE.md).
The original event status came from CTFd timing keys read by theme JavaScript;
there is no local persistent database from which to inspect production values.


## Ready platform typography and spacing — 2026-10-11

Platform Mode now shows “Platform ready” / “Ready to explore”, with no development
announcement. The same neutral status applies to challenge and scoreboard
headers. No event is enabled by this copy change.

The existing layout now uses larger Inter headings and body text, wider content,
a hero beside the platform panel on desktop, larger category/guide cards, and
compact section spacing. Inherited core-theme main padding and bottom margin
were removed. Mobile retains a single-column hero and panel, with readable
category cards and no horizontal overflow.


The updated ready-platform layout passes browser checks at 320/390/768/1440px,
mobile navigation and related-page rendering, with no JavaScript errors.
English/French/Arabic and RTL checks pass. The existing future-event status and
countdown checks and focused presentation unit checks also pass. Updated
screenshots use isolated QA fixture data.
