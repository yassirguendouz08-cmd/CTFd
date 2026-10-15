"""Publish the editable /rules page and its automatic navigation entry."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def install_rules(app, replace=False):
    from CTFd.cache import clear_pages
    from CTFd.models import Pages, db

    content = (ROOT / "docs/content/rules.md").read_text(encoding="utf-8")
    with app.app_context():
        page = Pages.query.filter_by(route="rules").first()
        desired = dict(title="Rules", content=content, format="markdown",
                       draft=False, hidden=False, auth_required=False, link_target=None)
        if page and all(getattr(page, key) == value for key, value in desired.items()):
            print("Rules page is already up to date.")
            return
        if page:
            if not replace:
                raise SystemExit("A rules page already exists. Use --replace to back it up and update it.")
            backup_dir = Path(app.config["UPLOAD_FOLDER"]) / "cyberdune-backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = backup_dir / ("rules-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
            fields = ("id", "route", *desired)
            backup.write_text(json.dumps({key: getattr(page, key) for key in fields}, indent=2), encoding="utf-8")
            print("Previous rules page backed up to:", backup)
        else:
            page = Pages(route="rules")
            db.session.add(page)
        for key, value in desired.items():
            setattr(page, key, value)
        db.session.commit()
        clear_pages()
        print("Published /rules. Edit it in Admin -> Pages; Rules appears in navigation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Back up and replace an existing rules page.")
    args = parser.parse_args()
    from CTFd import create_app
    install_rules(create_app(), replace=args.replace)
