# CyberDune theme guide

The custom theme lives in `CTFd/themes/cyberdune`, alongside the upstream CTFd
themes. It targets **CTFd 3.8.8**. Keep the `core` theme and `THEME_FALLBACK=True`:
CyberDune reuses compiled core assets and fallback templates. No npm build is needed.

## Activate

After finishing the initial CTFd setup:

```bash
docker compose exec ctfd python scripts/activate-cyberdune.py
docker compose restart ctfd
```

If earlier custom CSS is still pasted into Theme Header/Footer, the helper can
back up those fields and clear them:

```bash
docker compose exec ctfd python scripts/activate-cyberdune.py --clear-theme-injections
docker compose restart ctfd
```

Use that option when those fields contain only old theme snippets. If they also
contain required analytics/integrations, remove only the old CSS manually.
Backups are saved under `/var/uploads/cyberdune-backups/` in the persistent upload
directory. The helper prints the exact backup filename. Users, challenges, scores,
files and event rules are preserved.

Open forwarded port 80, refresh with **Ctrl+Shift+R**, and confirm `cyberdune` is
selected under **Admin → Config → Theme**.

## Edit the theme

| File | Purpose |
| --- | --- |
| `templates/components/copy.html` | English, French and Arabic branded copy |
| `templates/components/landing.html` | Homepage sections |
| `templates/components/navbar.html` | Navigation and three-language selector |
| `templates/components/contacts.html` | Official contact links |
| `templates/base.html` | Shared layout and CSS/JS cache versions |
| `static/css/cyberdune.css` | Style, responsive layout and RTL |
| `static/js/cyberdune.js` | Schedule, real homepage metrics, links and filters |
| `static/img/` | Supplied official white/red and black/red logos |

Copy uses the `cd_copy` macro and a translation dictionary shared with JavaScript.
Add all three variants when editing a phrase. User names, team names, challenge
content and custom admin pages are managed by the organizers. Core form labels
retain CTFd's translations, CSRF protection and validation.

The redesign removes the decorative terminal and animated background. Controls
respect reduced motion. Arabic uses RTL; code and flag fields retain LTR. Fonts
are self-hosted under `static/fonts`, with their OFL licenses.

The [Stitch references](stitch/README.md) record the actual generation and selected
variants. Homepage metrics/previews respect configured visibility and use CTFd
responses, never generated prototype figures. Admin CSS is included only when
CyberDune is selected and preserves its existing controls and editor.

Commit/push from your PC, then run `bash scripts/update-cyberdune.sh` in Codespaces.
Restarting CTFd reloads templates. For CSS/JS cache changes, increment the `?v=`
values in `templates/base.html`.

## Roll back

Select `core` in **Admin → Config → Theme**, or restore the configuration backup:

```bash
docker compose exec ctfd python scripts/activate-cyberdune.py --restore /var/uploads/cyberdune-backups/YOUR-BACKUP-FILENAME.json
docker compose restart ctfd
```

Use `git log` to find previous theme code. Git history and database backups are
separate; restoring code does not restore event data.

## Upgrade CTFd

Back up the database, uploads, application secret and theme configuration first.
Compare updated upstream challenge, auth, settings, team and user templates with
the custom overrides on staging. Preserve new fields, security checks, plugin
blocks and Alpine bindings. Check core asset paths and board/scoreboard contracts.

Validate registration, login, settings, teams, files, hints, flag attempts, solved
states, scores, profiles, languages, notifications and logout. See
[validation notes](VALIDATION.md) for completed checks and live limits.

## Operations visual layer

`static/css/operations.css` adds HUD corners, subtle card motifs, category icons,
input focus and standings highlights to the existing theme.
`templates/components/network.html` supplies the decorative hero SVG;
`static/js/operations.js` manages one-pass typing, motion preferences and finite
highlights on actual score/solve changes. The illustration is hidden from screen
readers; the terminal label has a stable accessible equivalent.

Colors and page grids remain in `cyberdune.css`. To adjust intensity, tune signal
opacity/timing in `operations.css`; do not modify challenge state or score APIs.
The hero pause button remembers its preference locally and reduced motion takes
priority. Cache version 10 loads the enhancement after the original CSS.
