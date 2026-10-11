# CYBERDUNE verification

Verified on 11 October 2026 against the supplied CTFd **3.8.8** source.
V7's editorial/layout changes pass the isolated application checks and desktop/mobile
browser suite; no theme runtime errors or unexpected failed requests. The revised
homepage was visually reviewed. These checks do not validate the live Codespace.
For v4, both official logo files are now supplied and bundled. The white/red version
was visually verified on dark desktop/mobile headers and footers. The application
and browser suites pass again, including logo asset responses and motion controls.
The old small side panel is removed. The live website was unavailable to the web
tool; the supplied website screenshot was used as the visual reference.
Reverified after the Desert Signal v2 redesign: all application checks and the
desktop/mobile browser suite pass; the SVG background loads successfully and
homepage screenshots were visually reviewed at 1440px and 390px.
Reverified for v3: full application/browser suite passes again. Additional tests
confirm actual command typing, pause/resume, persisted pause after reload, CSS
animation state, 390px viewport width, reduced-motion static fallback and no
JavaScript runtime errors. Animated desktop/mobile homepage screenshots reviewed.
Tests ran in an isolated local Flask application with an in-memory SQLite database.
Production Codespace data, accounts, uploads and configuration were not touched.

## Completed checks

- All custom Jinja templates compile under the real CTFd application.
- Visitor homepage, registration, login, content pages, challenge board, member
  list and scoreboard render successfully. Custom CSS/JS and core asset fallback
  resolve without missing assets.
- Registration, authenticated login/logout, settings and notifications routes.
- Challenge attachments, free hints, incorrect and correct flags, solved states,
  score changes, scoreboard results and public/private user profiles.
- A dynamic-scoring plugin challenge renders and accepts its correct flag.
- Teams mode enrollment, creation, joining and public/private team pages.
- Activation creates a persistent configuration backup, clears earlier theme
  injections when requested, and rollback restores the previous theme and CSS.
- Headless Brave/Playwright exercised real registration/login/logout forms,
  password visibility, challenge search/category/solved filters, details and files,
  scoreboard chart rendering and the current user's highlighted row.
- Browser checks at 390px, 768px and 1440px: navigation, forms, challenge dialog,
  homepage, challenge board, scoreboard, user profile and content pages. No
  horizontal viewport overflow was detected. Flag field receives keyboard focus.
- Fourteen screenshots were captured and representative desktop/mobile pages
  visually reviewed. Fixtures in those screenshots are synthetic test data;
  production templates fetch CTFd's actual data.

No theme JavaScript/Alpine runtime errors or unexpected failed requests were found.
CTFd's upstream anonymous notification stream requests `/events` and returns HTTP
403 for logged-out visitors. This expected request is recorded and allowed by the
test; the theme does not alter CTFd authentication or EventSource handling.

## Scope and live rollout checks

Earlier versions did not include the official logo in the source snapshot. V4
includes the subsequently supplied official artwork and uses its white/red version
on dark backgrounds. Confirm the bundled logo after activating in Codespace.

The browser used local SQLite rather than the Codespace MariaDB/Redis deployment.
The live Codespace has not been changed or verified by this implementation.
After installation, check forwarded port 80, your configured logo, event dates,
existing challenges, team mode, standings and one authorized test flag submission.

OAuth, email delivery, external challenge services, third-party plugins and every
possible bracket/freeze configuration were not exercised with live services.
Their upstream forms, hooks, endpoint calls and plugin template blocks remain
preserved; verify integrations you actually use before an event.

The admin dashboard remains the upstream CTFd interface. Recheck template/API
compatibility when upgrading CTFd, as described in THEME.md.
The delivered theme adds **no production dependencies**. Local QA dependencies,
test databases, test users, fixtures and browser scripts are excluded from the ZIP.

## V8 copy and language verification

New CyberDune copy renders in English, French and Arabic. Real browser checks
verified all three locales on home, login, register, challenges and scoreboard
at 390px, Arabic RTL, translated search empty states, the actual CTFd language
switch, and exactly en/fr/ar options in navbar and account settings. Desktop and
mobile form/challenge/scoreboard checks and terminal pause/reduced-motion checks
also passed. Live Codespace rollout remains user-applied.
