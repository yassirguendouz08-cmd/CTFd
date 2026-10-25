# Player UI improvements — 25 October 2026

Implemented in the deployed `core-theme` source and its generated assets, plus the instance challenge view.

- Quieter background: stronger dark overlay, still poster by default on inner pages, explicit animate/pause control. Reduced-motion preferences disable the background, text scrambling and ticker animations.
- Compact cards: responsive four/three/two/one-column layout, 176px desktop minimum height, clear points/solve labels and difficulty from organizer tags. Difficulty is never guessed from points.
- Progress: published challenge completion, private account/team score and ranking from the existing authenticated API. Hidden administrator previews do not count. Hidden ranking stays hidden; failed refreshes preserve the last value and offer Retry. A slow account API cannot block challenge loading.
- Navigation: direct Scoreboard and My team links; desktop navigation from 1024px, mobile menu below that, keyboard/outside-click dismissal retained.
- Instance panel: clear state badge, countdown, safe HTTP(S) Open link, copy feedback and expiration handling. Expired endpoints cannot be copied/opened. SSH instructions remain plain copyable text. Missing connection information displays Starting; invalid expiry requires a status recheck.
- Onboarding: profile/team/first-flag guide, highlighted team step for players without a team, dismissible per-account guide on the challenge board. New UI labels include French and Arabic translations.

## Validation

- Theme production build passed; existing ECharts large-chunk advisory remains nonblocking.
- Seven challenge-board JavaScript tests and three instance-panel tests passed (10 total).
- Focused isolated Python regression suite: 46 passed (localization, views, themes, teams and instance API).
- Additional team enrollment render check passed for a player without a team.
- Browser smoke tests with synthetic data: initial guide and dismissal; correct flag updated progress to 1/8, score to 100 and rank from the API; mocked instance reached Ready with countdown/Open/Copy; animation toggle plays/pauses; mobile menu opens/closes with Escape; EN/FR/AR labels checked. No JavaScript console errors recorded during the workspace checks.
- No horizontal overflow at 390px mobile or 1024px desktop in French; Arabic workspace direction verified RTL. Viewport overrides reset after checks.

No production accounts, flags, scores or settings were changed. The localhost fixture uses disposable SQLite and a mocked manager; real Docker startup was not exercised. Changes are local and require the existing VPS deployment process. Rebuild the theme with `npm ci && npm run build` in `CTFd/themes/core-theme` when preparing a clean deployment; include templates, static CSS/JS, manifest, compiled challenge bundle and plugin assets together. No database migration is required.

Screenshots and test/build logs are in `output/ui-improvements-2026-10-25` at the workspace root. Desktop screenshot shows synthetic challenges and a synthetic team.
