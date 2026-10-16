"""Import the four private drive exercises as admin-only, idempotent challenges."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PACK = "drive-training-v1"
SLUGS = {"hello-hex", "hidden-file", "archive-maze", "needle-log"}


def import_pack(app, directory):
    from werkzeug.datastructures import FileStorage
    from CTFd.cache import clear_challenges
    from CTFd.models import ChallengeFiles, Challenges, Flags, Hints, Tags, db
    from CTFd.utils.challenge_localization import training_catalog
    from CTFd.utils.uploads import get_uploader

    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest["challenges"]
    if manifest.get("pack") != PACK or len(entries) != 4 or {item["slug"] for item in entries} != SLUGS:
        raise ValueError("Expected exactly the four distinct supplied exercises.")
    catalogue = training_catalog()
    for item in entries:
        if item["value"] != 100 or len(item["hints"]) != 3 or len(item["files"]) != 1:
            raise ValueError("Expected 100 points, three free hints and one player attachment.")
        public = catalogue[item["slug"]]["fr"]
        if any(item[field] != public[field] for field in ("name", "description", "hints")):
            raise ValueError("Manifest text does not match the reviewed translation catalogue.")
        for filename in item["files"]:
            path = (directory / filename).resolve()
            if directory not in path.parents or not path.is_file():
                raise ValueError("Missing attachment or path outside pack.")
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"][path.name]:
                raise ValueError("Attachment integrity check failed.")
    if len({item["flag"] for item in entries}) != 4:
        raise ValueError("Answers must be distinct.")

    report, uploaded = [], []
    with app.app_context():
        uploader = get_uploader()
        try:
            for position, item in enumerate(entries, 101):
                marker = "drive-training:" + item["slug"]
                tag = Tags.query.filter_by(value=marker).first()
                challenge = Challenges.query.get(tag.challenge_id) if tag else None
                if challenge is None and Challenges.query.filter_by(name=item["name"]).first():
                    raise ValueError("Name collision outside this training pack.")
                if challenge:
                    if (any(getattr(challenge, key) != item[key] for key in ("name", "description", "category", "value"))
                            or challenge.state != "hidden" or challenge.type != "standard" or challenge.max_attempts != 0):
                        raise ValueError("Existing exercise was edited or published; refusing overwrite.")
                    flags = Flags.query.filter_by(challenge_id=challenge.id).all()
                    if len(flags) != 1 or flags[0].type != "static" or flags[0].content != item["flag"] or flags[0].data != item["flag_data"]:
                        raise ValueError("Existing exercise has different flags.")
                    hints = Hints.query.filter_by(challenge_id=challenge.id).order_by(Hints.id).all()
                    if [h.content for h in hints] != item["hints"] or any(h.cost for h in hints):
                        raise ValueError("Existing exercise has modified hints.")
                    saved = ChallengeFiles.query.filter_by(challenge_id=challenge.id).all()
                    expected = {Path(n).name: hashlib.sha1((directory / n).read_bytes()).hexdigest() for n in item["files"]}
                    if {Path(f.location).name: f.sha1sum for f in saved} != expected:
                        raise ValueError("Existing exercise has different attachments.")
                else:
                    challenge = Challenges(name=item["name"], description=item["description"], category=item["category"],
                                           value=100, type="standard", state="hidden", max_attempts=0, position=position, logic="any")
                    db.session.add(challenge)
                    db.session.flush()
                    db.session.add(Flags(challenge_id=challenge.id, type="static", content=item["flag"], data=item["flag_data"]))
                    for index, content in enumerate(item["hints"], 1):
                        db.session.add(Hints(challenge_id=challenge.id, title=f"Indice {index}", content=content, cost=0))
                    for value in ("Training", "Débutant", marker):
                        db.session.add(Tags(challenge_id=challenge.id, value=value))
                    for filename in item["files"]:
                        path = directory / filename
                        with path.open("rb") as stream:
                            location = uploader.upload(FileStorage(stream=stream, filename=path.name), path.name)
                        uploaded.append(location)
                        db.session.add(ChallengeFiles(challenge_id=challenge.id, location=location,
                                                      sha1sum=hashlib.sha1(path.read_bytes()).hexdigest()))
                report.append({"id": challenge.id, "slug": item["slug"], "name": challenge.name,
                               "category": challenge.category, "state": challenge.state,
                               "admin_url": f"/admin/challenges/{challenge.id}"})
            db.session.commit()
        except Exception:
            db.session.rollback()
            for location in uploaded:
                uploader.delete(location)
            raise
        clear_challenges()
    (directory / "import-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Imported 4 distinct hidden exercises; re-running does not duplicate records. No flags printed.")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    from CTFd import create_app
    import_pack(create_app(), args.directory)
