"""Training imports are idempotent, localized and private to administrators."""
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

from CTFd.models import ChallengeFiles, Challenges, Fails, Flags, Hints, Solves
from CTFd.utils import set_config
from CTFd.utils.challenge_localization import training_catalog
from tests.helpers import create_ctfd, destroy_ctfd, login_as_user, register_user


def test_drive_training_import_localization_and_access():
    spec = importlib.util.spec_from_file_location("import_drive_training", Path(__file__).parents[1] / "scripts/import-drive-training.py")
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    app = create_ctfd(ctf_theme="core-theme")
    try:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            entries = []
            for slug, translations in training_catalog().items():
                path = directory / slug / "evidence.txt"
                path.parent.mkdir()
                path.write_bytes(b"Disposable fixture evidence, no real challenge answers.")
                entries.append({
                    **translations["fr"], "slug": slug, "category": "Crypto" if slug == "hello-hex" else "Linux",
                    "value": 100, "flag": f"CYBERDUNE{{fixture_{slug}}}",
                    "flag_data": "case_insensitive" if slug == "hello-hex" else "",
                    "files": [f"{slug}/evidence.txt"],
                    "sha256": {"evidence.txt": hashlib.sha256(path.read_bytes()).hexdigest()},
                })
            (directory / "manifest.json").write_text(json.dumps({"pack": "drive-training-v1", "challenges": entries}), encoding="utf-8")
            app.config["UPLOAD_FOLDER"] = str(directory / "uploads")
            first = importer.import_pack(app, directory)
            assert first == importer.import_pack(app, directory)
            with app.app_context():
                assert Challenges.query.count() == Flags.query.count() == ChallengeFiles.query.count() == 4
                assert Hints.query.count() == 12 and all(h.cost == 0 for h in Hints.query.all())
                assert all(c.state == "hidden" and c.value == 100 for c in Challenges.query.all())
                files = {f.challenge_id: f.location for f in ChallengeFiles.query.all()}
                hints = {row["id"]: [h.id for h in Hints.query.filter_by(challenge_id=row["id"]).order_by(Hints.id)] for row in first}
                set_config("challenge_visibility", "public")
                register_user(app)
            with login_as_user(app, "admin") as admin:
                for language in ("en", "fr", "ar", "en"):
                    admin.set_cookie("language", language, domain="localhost")
                    listing = admin.get("/api/v1/challenges?localized=1").get_json()["data"]
                    by_id = {c["id"]: c for c in listing}
                    for row in first:
                        cid = row["id"]
                        expected = training_catalog()[row["slug"]][language]
                        assert by_id[cid]["name"] == expected["name"]
                        data = admin.get(f"/api/v1/challenges/{cid}?localized=1").get_json()["data"]
                        assert data["name"] == expected["name"] and data["description"] == expected["description"]
                        assert "drive-training:" not in data["view"]
                        for index, hid in enumerate(hints[cid]):
                            assert "content" not in data["hints"][index]
                            hint = admin.get(f"/api/v1/hints/{hid}?localized=1&preview=1").get_json()["data"]
                            assert hint["content"] == expected["hints"][index]
                for row, item in zip(first, entries):
                    cid = row["id"]
                    assert admin.get("/files/" + files[cid]).status_code == 200
                    for value, status in ((item["flag"], "correct"), ("CYBERDUNE{wrong}", "incorrect")):
                        result = admin.post("/api/v1/challenges/attempt", json={"challenge_id": cid, "submission": value}).get_json()["data"]
                        assert result["status"] == status and result["preview"] is True
                result = admin.post("/api/v1/challenges/attempt", json={"challenge_id": first[0]["id"], "submission": entries[0]["flag"].lower()}).get_json()["data"]
                assert result["status"] == "correct"
            for client in (app.test_client(), login_as_user(app)):
                assert client.get("/api/v1/challenges?localized=1").get_json()["data"] == []
                for row in first:
                    cid = row["id"]
                    assert client.get(f"/api/v1/challenges/{cid}?localized=1").status_code == 404
                    assert client.get(f"/api/v1/hints/{hints[cid][0]}?localized=1").status_code == 404
                    assert client.get("/files/" + files[cid]).status_code == 404
            # An evidence mismatch must fail before creating or changing records.
            (directory / entries[0]["files"][0]).write_bytes(b"tampered")
            try:
                importer.import_pack(app, directory)
                raise AssertionError("Tampered attachment was accepted")
            except ValueError:
                pass
            with app.app_context():
                assert Challenges.query.count() == 4
                assert Solves.query.count() == Fails.query.count() == 0
    finally:
        destroy_ctfd(app)
