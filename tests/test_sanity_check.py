import importlib.util
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from CTFd.models import Challenges, Fails, Flags, Notifications, Pages, Solves, db
from tests.helpers import create_ctfd, destroy_ctfd, login_as_user, register_user


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def test_sanity_source_announcement_player_access_and_retry():
    spec = importlib.util.spec_from_file_location(
        "sanity_import", Path(__file__).resolve().parents[1] / "scripts/import-sanity-check.py")
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    app = create_ctfd()
    try:
        original = "# CTF Rules\n\nKeep this organizer-written rule.\n"
        with app.app_context():
            db.session.add(Pages(route="rules", title="Rules", content=original,
                                 format="markdown", draft=False, hidden=False, auth_required=False))
            db.session.commit()
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "answer.json"
            flag = "CYBERDUNE{synthetic_source_test_012345}"
            private.write_text(json.dumps({"challenge": importer.MARKER, "flag": flag}))
            report = importer.publish(app, private)
            assert report["state"] == "visible" and report["value"] == 50
            assert importer.publish(app, private) == report
            assert len(list(Path(directory).glob("rules-before-sanity-*.json"))) == 1
            register_user(app)
            player = login_as_user(app)
            cid = report["id"]
            listing = player.get("/api/v1/challenges").get_json()["data"]
            assert cid in {row["id"] for row in listing}
            detail = player.get(f"/api/v1/challenges/{cid}")
            assert detail.status_code == 200 and flag not in detail.get_data(as_text=True)
            # Test the actual delivered document, including when HTML sanitization is on.
            for sanitize in (False, True):
                app.config["HTML_SANITIZATION"] = sanitize
                response = player.get("/rules")
                assert response.status_code == 200
                html = response.get_data(as_text=True)
                assert importer.COMMENT_START + flag + "\n-->" in html
                parser = VisibleText()
                parser.feed(html)
                assert flag not in "".join(parser.parts)
                assert "Keep this organizer-written rule." in html
            assert importer.TITLE in player.get("/notifications").get_data(as_text=True)
            with app.app_context():
                assert Challenges.query.count() == 1
                assert Flags.query.filter_by(challenge_id=cid).count() == 1
                assert Notifications.query.filter_by(title=importer.TITLE).count() == 1
                assert Pages.query.filter_by(route="rules").one().content.startswith(original.rstrip())
            for submission, expected in (("CYBERDUNE{wrong}", "incorrect"), (flag, "correct")):
                response = player.post("/api/v1/challenges/attempt", json={
                    "challenge_id": cid, "submission": submission})
                assert response.status_code == 200
                assert response.get_json()["data"]["status"] == expected
            assert importer.publish(app, private) == report
            with app.app_context():
                assert Solves.query.filter_by(challenge_id=cid).count() == 1
                assert Fails.query.filter_by(challenge_id=cid).count() == 1
                page = Pages.query.filter_by(route="rules").one()
                page.content = page.content.replace(flag, "CYBERDUNE{edited_by_organizer}")
                db.session.commit()
            with unittest.TestCase().assertRaisesRegex(ValueError, "different Sanity Check flag"):
                importer.publish(app, private)
            with app.app_context():
                assert "CYBERDUNE{edited_by_organizer}" in Pages.query.filter_by(route="rules").one().content
                assert Notifications.query.count() == 1
    finally:
        destroy_ctfd(app)
