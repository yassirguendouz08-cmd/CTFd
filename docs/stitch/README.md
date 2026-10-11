# CyberDune × Google Stitch

[Open the actual Stitch project](https://stitch.withgoogle.com/projects/10465941215322521387)

Project: `10465941215322521387`. Shared system: `4cd60b4296b84f7b87dc958737fa3ba4`.
The artifacts below came from actual Google Stitch MCP generation and variant
calls, authenticated against Google's official endpoint. They are design references,
not deployed Tailwind prototypes. The generated landing was independently retrieved
with `get_screen`; IDs and exports are recorded in [manifest.json](manifest.json).

## Selection and implementation

Selected landing variant 1: a clear split hero with an aligned briefing panel.
Variant 2 introduced a technical terminal/table treatment that made the landing
less approachable and repeated event details. The refined challenge variant keeps
search, solved-state filtering and legible challenge details while reducing clutter.
The mobile variant informs stacked hero/briefing and two-column category cards.

Production uses the supplied official logo rather than generated wordmarks. Fonts
are self-hosted. The shared visual system covers landing, auth/recovery, challenges,
modal, scoreboard, profiles, teams, content and announcements. Admin appearance
is opt-in when CyberDune is selected; existing admin structure and scripts remain.

Stitch added sample policies, dates, divisions, contacts and infrastructure to some
prototypes. Those values are not authoritative and were not transferred to the app.
Metrics, categories and top-three preview use authorized CTFd API responses; event
dates and format use configuration. Original auth fields, hint purchases, attempts,
flag validation, scoring, brackets, permissions and plugin hooks stay intact.

## Actual generated screen exports

| Screen | Stitch screen ID | Export |
| --- | --- | --- |
| CYBERDUNE CTF — Official Competition Landing | `08cda9e80cc0433196f6e94e47a2f7c0` | [PNG](exports/landing.png) · [HTML](exports/landing.html) |
| CYBERDUNE CTF — Operational Workspace (Variant 1) | `811c3aec8fb84afc94dcf715250386b5` | [PNG](exports/landing-variant-1.png) · [HTML](exports/landing-variant-1.html) |
| CYBERDUNE CTF — Operational Workspace (Variant 2) | `4ae1b6df2d2242d2912c8a4ca5ad7fa7` | [PNG](exports/landing-variant-2.png) · [HTML](exports/landing-variant-2.html) |
| CYBERDUNE CTF — Challenge Board & Operational Workspace | `6eed556f040b4b7ea82f1f060579cf46` | [PNG](exports/board.png) · [HTML](exports/board.html) |
| CYBERDUNE CTF — Refined Challenge Workspace | `46c4a31a66414d4dabb3da3a8bd35da3` | [PNG](exports/board-variant.png) · [HTML](exports/board-variant.html) |
| CYBERDUNE CTF — Player & Team Login | `5c6846fe9f4b470389e02a7deeb5f04c` | [PNG](exports/auth-1.png) · [HTML](exports/auth-1.html) |
| CYBERDUNE CTF — Password Recovery | `5e145fe1ad8c41d3a2df6ccba074b428` | [PNG](exports/auth-2.png) · [HTML](exports/auth-2.html) |
| CYBERDUNE CTF — Account Registration | `382668072147482a921535a19b44f094` | [PNG](exports/auth-3.png) · [HTML](exports/auth-3.html) |
| CYBERDUNE CTF — Let your solves speak (Scoreboard) | `229b529ac5554f0480e974a01acc6d21` | [PNG](exports/competition-1.png) · [HTML](exports/competition-1.html) |
| CYBERDUNE CTF — Operator & Squad Profile | `8d1fefba82724125be8d266bcfe33e13` | [PNG](exports/competition-2.png) · [HTML](exports/competition-2.html) |
| CYBERDUNE CTF — Event Information & Operations Guide | `bbcf5b071b5248b5a315df85ab9cd8b0` | [PNG](exports/competition-3.png) · [HTML](exports/competition-3.html) |
| CYBERDUNE CTF — Mobile Landing & Briefing | `83d1fdb34a2245d2b16f3750c2e1f7c7` | [PNG](exports/mobile.png) · [HTML](exports/mobile.html) |

The private project requires the same Google account to open. Local exported PNGs
and HTML remain reviewable independently. The API credential is stored outside
the application repository and is not required to run the CTF platform.

## Rollout

Push the local `platform` checkout to GitHub, then run
`bash scripts/update-cyberdune.sh` in Codespaces and refresh with Ctrl+Shift+R.
If an older pasted Theme Header/Footer overrides the theme, follow [THEME.md](../THEME.md).
Baseline code checkpoint: `7832aa34`. The local test database is isolated; deployed
MariaDB, Redis and email delivery require the live rollout checks in [VALIDATION.md](../VALIDATION.md).

## Advanced visual enhancement

The existing selected landing was refined with the official `edit_screens` tool,
not regenerated from scratch. Screen `1fe2bf7df4c9494386f03bfccdb6a423` adds
angular network paths, sparse signal nodes, a terminal label, motion controls and
HUD accents. [PNG](exports/operations-enhanced.png) · [HTML](exports/operations-enhanced.html).
The export is a visual reference only: its sample dates, coordinates, policies and
telemetry are not deployed or treated as real event data. The application keeps
its existing layout, copy, palette, official logos and authorized CTFd metrics.
