# Dead Letter — The Conflicting Catalogue

A hard, 500-point OSINT investigation using public maritime archive metadata.
Players identify an archive collection, follow sibling records, distinguish a
map's subject from its deposit location, and resolve conflicting catalogue dates.
The challenge is English, with three optional free progressive hints and unlimited
attempts. No downloadable evidence or running instance is necessary.

The importer explicitly publishes it as **Visible**, with no schedule, module or
prerequisite. Existing platform access rules still apply. It does not release any
hidden training challenges or change scores, accounts or event configuration.

Keep the private answer and organizer walkthrough outside this repository.
The answer JSON has `challenge` set to `hard-osint:dead-letter-v1` and a `flag`
field. The flag uses the format documented in the player description.

Run inside the CTFd container:

```sh
python scripts/import-hard-osint.py /private/dead-letter/answer.json
```

Repeating the same import verifies the existing record without duplicating it.
Edited challenges, hints, tags or answers cause an error instead of being replaced.
After publication, check `/api/v1/challenges` and the challenge detail as a regular
player. Verify the flag with the static flag comparator or an isolated test
database; do not submit a correct flag on a live player account just for testing.

Public source URLs belong in the private organizer guide because they directly
reveal the research destination. The museum metadata was checked on 17 October
2026. Recheck source availability before using this challenge in an event.
