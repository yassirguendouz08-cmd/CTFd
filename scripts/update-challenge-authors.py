"""Apply the organizer's author credits to the existing supplied challenges."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from CTFd import create_app
from CTFd.cache import clear_challenges
from CTFd.models import Challenges, Tags, Users, db
from sqlalchemy import inspect


def update_authors(app):
    mentro_challenges = {"TRANSITION", "VAULT", "The capital", "The Rogue", "Report", "Holy"}
    with app.app_context():
        changes, before, selected = [], {}, []
        for challenge in Challenges.query.order_by(Challenges.id).all():
            tags = {tag.value for tag in Tags.query.filter_by(challenge_id=challenge.id).all()}
            if not (challenge.category.strip().casefold() in {"linux", "reverse engineering"}
                    or any(t.startswith(("bootcamp-first-steps:", "drive-training:")) for t in tags)
                    or challenge.name.strip() in mentro_challenges):
                continue
            before[challenge.id] = {column.key: getattr(challenge, column.key)
                                    for column in inspect(Challenges).column_attrs}
            author = {"linux": "Soussi", "reverse engineering": "Mentro"}.get(
                challenge.category.strip().casefold(), "Yass1ir")
            if challenge.name.strip() in mentro_challenges:
                author = "Mentro"
            selected.append((challenge.id, author))
            changes.append({"id": challenge.id, "name": challenge.name,
                            "before": challenge.attribution, "after": author})
        if not selected:
            raise RuntimeError("No supplied challenges found")
        backup = Path("/tmp") / ("challenge-authors-before-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        backup.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
        backup.chmod(0o600)
        for cid, author in selected:
            db.session.get(Challenges, cid).attribution = author
        db.session.commit()
        clear_challenges()
        db.session.expire_all()
        for cid, author in selected:
            challenge = db.session.get(Challenges, cid)
            assert challenge.attribution == author
            assert all(getattr(challenge, key) == value for key, value in before[cid].items() if key != "attribution")
        admin = Users.query.filter_by(type="admin", banned=False).first()
        client = app.test_client()
        with client.session_transaction() as session:
            session["id"] = admin.id
            session["nonce"] = "author-verification"
        for cid, author in selected:
            response = client.get(f"/api/v1/challenges/{cid}?localized=1")
            assert response.status_code == 200
            data = response.get_json()["data"]
            assert data["attribution"] == author
            assert author in data["view"] and "cyber-meta-label" in data["view"]
        print(json.dumps({"verified": changes, "backup": str(backup)}, ensure_ascii=False))


if __name__ == "__main__":
    update_authors(create_app())
