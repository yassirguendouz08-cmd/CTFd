import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from CTFd.models import Challenges, Fails, Flags, Hints, Solves, db
from tests.helpers import create_ctfd, destroy_ctfd, login_as_user, register_user


def test_hard_osint_publication_player_access_and_preservation():
    spec = importlib.util.spec_from_file_location(
        "hard_osint_import", Path(__file__).resolve().parents[1] / "scripts/import-hard-osint.py"
    )
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    app = create_ctfd()
    try:
        with app.app_context():
            untouched = Challenges(name="Existing private exercise", category="OSINT",
                                   type="standard", state="hidden", value=100)
            db.session.add(untouched)
            db.session.commit()
            untouched_id = untouched.id
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "answer.json"
            # A synthetic test answer; never the production flag.
            answer = "CYBERDUNE{test-9-1_test-9-2_fixture_19010102}"
            private.write_text(json.dumps({"challenge": importer.MARKER, "flag": answer}), encoding="utf-8")
            report = importer.publish(app, private)
            cid = report["id"]
            assert report["state"] == "visible" and report["value"] == 500
            assert importer.publish(app, private) == report
            register_user(app)
            player = login_as_user(app)
            listed = player.get("/api/v1/challenges?localized=1")
            assert listed.status_code == 200
            ids = {row["id"] for row in listed.get_json()["data"]}
            assert cid in ids and untouched_id not in ids
            detail = player.get(f"/api/v1/challenges/{cid}?localized=1")
            assert detail.status_code == 200
            data = detail.get_json()["data"]
            assert data["name"] == importer.NAME and data["state"] == "visible"
            assert answer not in detail.get_data(as_text=True)
            assert player.get("/challenges").status_code == 200
            with app.app_context():
                assert Challenges.query.count() == 2
                assert Flags.query.filter_by(challenge_id=cid).count() == 1
                assert Hints.query.filter_by(challenge_id=cid).count() == 3
                assert Challenges.query.get(untouched_id).state == "hidden"
            for submission, status in (("CYBERDUNE{wrong}", "incorrect"), (answer.lower(), "correct")):
                attempt = player.post("/api/v1/challenges/attempt", json={
                    "challenge_id": cid, "submission": submission,
                })
                assert attempt.status_code == 200
                assert attempt.get_json()["data"]["status"] == status
            assert importer.publish(app, private) == report
            with app.app_context():
                assert Solves.query.filter_by(challenge_id=cid).count() == 1
                assert Fails.query.filter_by(challenge_id=cid).count() == 1
                challenge = Challenges.query.get(cid)
                challenge.description = "Organizer edited the description"
                db.session.commit()
            with unittest.TestCase().assertRaisesRegex(ValueError, "edited"):
                importer.publish(app, private)
            with app.app_context():
                assert Challenges.query.get(cid).description == "Organizer edited the description"
                assert Solves.query.filter_by(challenge_id=cid).count() == 1
    finally:
        destroy_ctfd(app)
