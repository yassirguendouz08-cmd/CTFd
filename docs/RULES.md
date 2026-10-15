# Public CTF rules

The public `/rules` page uses CTFd's native Pages system. Its visible **Rules**
navigation link is supplied automatically by the theme's page menu.

Publish the versioned copy in `docs/content/rules.md` inside the CTFd container:

```bash
~/ctfd-compose exec -T ctfd python scripts/install-rules.py --replace
```

The installer creates the page or backs up an existing page before replacing it.
It clears only page caches. Repeating the command with identical content makes
no changes. It does not change accounts, challenges, scores, or competition settings.

After publishing, edit **Admin → Pages → Rules** to adjust the rules. Set team
limits, schedules, eligibility, and tool restrictions in the announcements for
each event. Rerunning the installer with `--replace` restores the versioned text,
so commit any editorial changes you want to preserve first.
