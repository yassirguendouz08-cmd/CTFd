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

Decorative terminal/background animations are removed; earlier animation tests
are historical. Reduced-motion CSS disables transitions. Fonts are locally served
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
