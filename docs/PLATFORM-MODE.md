# CYBERDUNE platform and event presentation

Platform Mode is the default. Existing or sample CTFd dates never activate an
event. The homepage shows CYBERDUNE CTF PLATFORM, the development status,
upcoming competitions and the learning mission, using the existing theme.
Challenge navigation and all CTFd features remain available under their existing
permissions. Homepage participant metrics and standings previews appear only
in Event Mode and use authorized CTFd API data; no invented statistics exist.

## Where the old event information came from

The original `components/landing.html` contained a theme Mission briefing with
date/status/countdown placeholders. `base.html` supplied the CTFd database
configuration keys `start` and `end` to `cyberdune.js`, which inferred a live
event from dates alone. Challenge and scoreboard headers used the same logic.
Dates were not hardcoded in these templates. Homepage category and standings
metrics used real API data. Prior local edits removed the homepage briefing but
left the date-driven status logic on related pages.

CTFd stores timings in its `configs` table, administered under **Admin → Config
→ CTF Time**. The local Windows source checkout has no persistent database or
running Docker deployment; QA uses a separate in-memory fixture database.
The actual deployed values therefore cannot be asserted from this checkout.

## Put an existing deployment into development mode

After deploying this source and restarting CTFd, missing `cyberdune_mode` settings
already render Platform Mode, regardless of saved dates. To explicitly select it
and remove stale CTFd timing gates, run inside the existing deployment:

```bash
docker compose exec ctfd python scripts/platform-mode.py
docker compose exec ctfd python scripts/platform-mode.py --apply
docker compose restart ctfd
```

The first command only reports current start/end/freeze values. The second backs
up `theme_settings`, `start`, `end`, and `freeze` under the configured upload
folder's `cyberdune-backups/`, preserves other theme settings, selects Platform
Mode, and clears those three timing keys in one transaction. It never changes
challenges, accounts, teams, flags, submissions, uploads, or saved pages. Clearing
timing gates allows practice under the existing visibility and access settings.
If PRESET_CONFIGS overrides these keys in your deployment, update that preset
configuration too; CTFd presets take precedence over database configuration.

Alternatively, select **Admin → Config → Theme → Theme Settings → Build →
CYBERDUNE presentation mode → Platform**, click **Update** in the builder, then
**Update** on the Theme tab. Clear obsolete Start, End, and Freeze timings under
**CTF Time** and save. The mode setting changes presentation only; timings
continue to control CTFd's own access/scoring rules until cleared.

## Activate a real future event

1. Set the real competition name in **Admin → Config → General → CTF Name**.
2. Set and save real **Start Time** and **End Time** in **Config → CTF Time**.
   Check the displayed timezone and UTC timestamps. Both must be present and
   positive; End must be later than Start.
3. Open **Config → Theme → Theme Settings → Build**. Select **Event** in
   **CYBERDUNE presentation mode**, and enter the optional plain-text Event
   briefing. Click **Update** in the builder, then **Update** on the Theme tab.
4. Refresh the homepage. Verify the name, dates, status, and intended CTFd
   challenge/scoreboard/registration visibility before announcing the event.

Upcoming events count down to Start. Live events count down to End. Ended events
show their real dates and ended status without a countdown. Status is rendered
on the server and refreshed in the browser. Dates include the browser's local
timezone; server-rendered fallback dates are ISO 8601 UTC. A missing/invalid
schedule or name falls back to Platform Mode even if Event was selected.

Settings use CTFd's existing `theme_settings` JSON (`cyberdune_mode: "platform"`
or `"event"`, and `cyberdune_event_briefing`). The small
`cyberdune_presentation` plugin reads these settings without changing CTFd rules
or writing data. Keep plugins enabled (`SAFE_MODE=False`) for Event Mode; if the
plugin is unavailable the templates fall back to Platform Mode.

Stored index-page content is suppressed on the homepage in Platform Mode to
prevent old event announcements from resurfacing. It is preserved in the database
and rendered again in Event Mode; review it in Admin → Pages before activation.
Other custom pages and theme header/footer injections retain their normal CTFd
behavior, so review any announcements you previously entered there as well.

To return to Platform Mode later, select Platform in the same builder and save.
Use the backed-up helper if the competition timing gates should also be cleared.
