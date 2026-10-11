# Supplied CyberDune theme

The theme from `core-theme.zip` is installed in `CTFd/themes/core-theme`.
It includes the supplied glass navigation, red challenge cards, homepage,
profile pages, compiled assets and animated images. Its original license is
preserved; the visible footer credit is Yassir Guendouz, as requested. The archive's Git history and maintenance
scripts are not installed.

Activate it in your running Codespace or Docker host after updating the source:

```bash
docker compose exec ctfd python scripts/activate-cyberdune.py --clear-theme-injections
docker compose restart ctfd
```

The helper defaults to `core-theme`, backs up the current theme configuration
under the configured upload folder, and clears old header/footer injections
only when the shown flag is passed. It does not change users, challenges,
scores, pages, flags or event dates. The admin theme selector also offers
`core-theme`.

To select the previous theme, use `--theme cyberdune`. To restore the exact
previous configuration, use `--restore /path/to/theme-backup.json` with the
backup path printed by the helper, then restart CTFd.

Integration changes repair original-server image references, serve theme assets
under the configured application prefix, expose mobile navigation, allow page
scrolling, render challenge styles inside the inherited content block and use
the existing platform/event presentation settings for the countdown. The
homepage uses the supplied `pagehome.html`; other database pages still render
their existing content. Outdated RamaDune dates and registration claims were
removed from the homepage copy.

The provided compiled assets are ready to serve; no frontend build is needed.
External Google Fonts remain in the original theme and fall back to monospace.

Validation used an isolated CTFd database: template compilation, public and
account routes, all local static assets, challenge rendering and successful
flag submission. Desktop and mobile browser checks cover horizontal overflow,
images, navigation and JavaScript errors.
