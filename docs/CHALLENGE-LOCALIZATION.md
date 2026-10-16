# Challenge language

The core-theme challenge board follows the platform language selector (English,
French, Arabic) for the eight first-steps exercises and four supplied training exercises: cards, descriptions, hints,
tags, categories and challenge controls. Arabic challenge content uses RTL while
flag inputs keep their left-to-right direction.

`CTFd/utils/challenge_localization/bootcamp.json` contains public teaching text.
The `bootcamp-first-steps:<slug>` tag identifies a translation entry independently
of database IDs. `ui.json` contains the challenge and navigation labels. Never
add real flags, solutions or organizer manifests to either catalogue.

The player board opts into localized GET responses using `localized=1`. This
also lets administrators preview translated hidden challenges from the normal
board. Administrative editing calls keep their canonical source content.
Translations are applied after existing visibility, prerequisites and hint unlock
checks. A locked hint never acquires content through translation.

Localization copies response data and uses a template view proxy; it does not
update database records or cached challenge objects. Flags, attachments, points,
solve history and hidden states remain unchanged. Downloaded evidence files keep
their original bytes, names and identifiers so the exercises remain reproducible.

To add a new exercise, add an explicitly reviewed catalogue entry and matching
tag. An exercise without an entry retains its authored content. If an organizer
edits a French source field, that field immediately falls back to the new source
instead of displaying an outdated translation; update the catalogue's French
source and translations together. Hints match by source content rather than order
or database ID.

Validation: `tests/test_challenge_localization.py` alternates en/fr/ar/en in the
same process, checks every description and hint, verifies user language preference,
locked hints and hidden challenges, confirms source-edit fallback, and checks that
flags, source records and score counts are unchanged.

The four supplied training exercises use `drive-training.json` and the
`drive-training:<slug>` tag. Their importer and source mapping are documented in
`challenges/drive-training/README.md`.
