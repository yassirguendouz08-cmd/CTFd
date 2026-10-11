"""Inspect or enable CYBERDUNE Platform Mode inside the CTFd container."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Back up settings, enable Platform Mode and clear start/end/freeze timing gates.")
    args = parser.parse_args()
    from CTFd import create_app
    from CTFd.models import Configs, db
    from CTFd.cache import cache
    from CTFd.utils import get_config
    app = create_app()
    with app.app_context():
        keys = ("theme_settings", "start", "end", "freeze")
        values = {key: get_config(key) for key in keys}
        print("CTFd timing configuration (UTC timestamps):", json.dumps({key: values[key] for key in keys if key != "theme_settings"}))
        if not args.apply:
            print("Read-only inspection. Use --apply to enable Platform Mode and clear timings with a backup.")
            return
        try:
            settings = json.loads(values["theme_settings"] or "{}")
        except (TypeError, ValueError):
            raise SystemExit("Invalid theme_settings JSON. Repair it in Admin before applying Platform Mode.")
        if not isinstance(settings, dict):
            raise SystemExit("theme_settings must be a JSON object.")
        backup_dir = Path(app.config["UPLOAD_FOLDER"]) / "cyberdune-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / ("platform-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        backup.write_text(json.dumps(values, indent=2), encoding="utf-8")
        backup.chmod(0o600)
        settings["cyberdune_mode"] = "platform"
        updated = {"theme_settings": json.dumps(settings), "start": None, "end": None, "freeze": None}
        # Commit all four configuration rows together; never touch competition data.
        for key, value in updated.items():
            row = Configs.query.filter_by(key=key).first()
            if row is None:
                db.session.add(Configs(key=key, value=value))
            else:
                row.value = value
        db.session.commit()
        cache.clear()
        print("Platform Mode enabled; start/end/freeze cleared. Backup:", backup)


if __name__ == "__main__":
    main()
