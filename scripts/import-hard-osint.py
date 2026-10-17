"""Publish Dead Letter from a private answer file; never overwrite existing work."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NAME = "Dead Letter — The Conflicting Catalogue"
MARKER = "hard-osint:dead-letter-v1"
DESCRIPTION = """**Hard · OSINT · 500 points**

A southern harbour named for a winter holiday. A metal container beneath stones.
Its papers connect an oceanographic voyage, an Arctic rescue search and a polar
epitaph. A neighbouring archive record describes a tracing of a different island.
The catalogue descriptions disagree about when the container was recovered.

Reconstruct the trail using public museum catalogues. Find:

1. The **item reference** of the record containing the messages and epitaph.
2. The **item reference** of its sibling record describing the tracing.
3. The **island depicted by the tracing**, not the island where it was deposited.
4. The **full recovery date stated in the tracing's own description**, not its
   creation date or the year stated in the messages record.

**Flag:** `CYBERDUNE{messages-reference_tracing-reference_island_YYYYMMDD}`

Replace each slash in a reference with a hyphen. Lowercase the island name, remove
the standalone word `Island`, and join any remaining words with hyphens. The flag
is case-insensitive. A fictional formatting example is
`CYBERDUNE{abc-7-1_abc-7-2_example_19001231}`.

No account, paid archive access, scanning or contact with anyone is required.
Public catalogue metadata is enough; you do not need to request the manuscripts.
Keep the source URLs and distinguish catalogue statements from historical certainty.
"""
HINTS = (
    "Start with the location and the container. Search for maritime museum archives, rather than modern social profiles.",
    "The holding institution is Royal Museums Greenwich. Search its collections for the container and follow the archive hierarchy to the sibling item.",
    "Open both item descriptions. Use the tracing record's recovery date, not the messages record's year or the tracing's Date made field. Item references are not website object IDs.",
)
TAGS = ("Hard", "Archival research", "Source verification", MARKER)


def publish(app, answer_file):
    from CTFd.cache import clear_challenges
    from CTFd.models import Challenges, Flags, Hints, Tags, db

    payload = json.loads(Path(answer_file).read_text(encoding="utf-8"))
    answer = payload.get("flag", "")
    if payload.get("challenge") != MARKER or not re.fullmatch(
        r"CYBERDUNE\{[a-z0-9-]+_[a-z0-9-]+_[a-z-]+_[0-9]{8}\}", answer
    ):
        raise ValueError("Expected a private Dead Letter answer file and canonical flag.")
    expected = dict(name=NAME, category="OSINT", description=DESCRIPTION,
                    value=500, type="standard", state="visible", max_attempts=0,
                    logic="any", attribution="Yass1ir", requirements=None,
                    scheduled_at=None, module_id=None)
    with app.app_context():
        try:
            matches = Challenges.query.join(Tags).filter(Tags.value == MARKER).all()
            if len(matches) > 1:
                raise ValueError("Duplicate marker; review manually.")
            if matches:
                challenge = matches[0]
                if any(getattr(challenge, key) != value for key, value in expected.items()):
                    raise ValueError("Existing challenge was edited; refusing overwrite.")
                flags = Flags.query.filter_by(challenge_id=challenge.id).all()
                hints = Hints.query.filter_by(challenge_id=challenge.id).order_by(Hints.id).all()
                if (len(flags) != 1 or flags[0].content != answer or
                        flags[0].type != "static" or flags[0].data != "case_insensitive" or
                        [(h.title, h.content, h.cost) for h in hints] !=
                        [(f"Hint {i}", content, 0) for i, content in enumerate(HINTS, 1)] or
                        sorted(t.value for t in challenge.tags) != sorted(TAGS)):
                    raise ValueError("Existing answers, hints or tags differ; refusing overwrite.")
            else:
                if Challenges.query.filter_by(name=NAME).first():
                    raise ValueError("Name belongs to another challenge; refusing overwrite.")
                challenge = Challenges(**expected)
                db.session.add(challenge)
                db.session.flush()
                db.session.add(Flags(challenge_id=challenge.id, type="static",
                                     content=answer, data="case_insensitive"))
                for i, content in enumerate(HINTS, 1):
                    db.session.add(Hints(challenge_id=challenge.id, title=f"Hint {i}",
                                         content=content, cost=0))
                for value in TAGS:
                    db.session.add(Tags(challenge_id=challenge.id, value=value))
            db.session.commit()
            report = dict(id=challenge.id, name=challenge.name, category=challenge.category,
                          value=challenge.value, state=challenge.state,
                          player_url=f"/challenges#{challenge.id}",
                          admin_url=f"/admin/challenges/{challenge.id}")
        except Exception:
            db.session.rollback()
            raise
        clear_challenges()
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answer_file", type=Path, help="Private JSON with challenge marker and flag.")
    args = parser.parse_args()
    from CTFd import create_app
    publish(create_app(), args.answer_file)
