"""Publish Sanity Check, hide its flag in /rules source, and announce it once."""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NAME = "Sanity Check"
MARKER = "sanity-check:rules-source-v1"
COMMENT_START = "<!-- cyberdune-sanity-check:v1\n"
TITLE = "Sanity Check — Read the Rules"
DESCRIPTION = """**Welcome · 50 points**

Before you start hunting, read the [Rules](/rules).
A flag is hidden in that page's **HTML source code**.

Use your browser's **View Page Source** (`Ctrl+U` on Windows/Linux), find the
`CYBERDUNE{...}` flag, then submit it here. On mobile, use your browser's source
viewer or download the page HTML. No scanning or exploitation is needed.
"""
ANNOUNCEMENT = """**Sanity Check is available — 50 points!**

A flag is hidden in the **HTML source code of the [Rules page](/rules)**.
Read the rules, open **View Page Source** (`Ctrl+U` on Windows/Linux), search for
`CYBERDUNE{`, and submit the complete flag to **Sanity Check** on the
[Challenges board](/challenges).

**Darija:** Lflag mkhebbi f source code dyal page Rules. 7ell Rules, dir
View Page Source (Ctrl+U), 9elleb 3la lflag w submitih f Sanity Check.
"""


def publish(app, answer_file):
    from CTFd.cache import clear_challenges, clear_pages
    from CTFd.models import Challenges, Flags, Notifications, Pages, Tags, db
    from CTFd.schemas.notifications import NotificationSchema

    answer_file = Path(answer_file).resolve()
    data = json.loads(answer_file.read_text(encoding="utf-8"))
    flag = data.get("flag", "")
    if data.get("challenge") != MARKER or not re.fullmatch(r"CYBERDUNE\{[a-zA-Z0-9_]{8,100}\}", flag):
        raise ValueError("Expected a private Sanity Check answer file.")
    comment = COMMENT_START + flag + "\n-->"
    created_notice = False
    with app.app_context():
        try:
            page = Pages.query.filter_by(route="rules").one_or_none()
            if not page or page.draft or page.auth_required or page.format not in ("html", "markdown"):
                raise ValueError("Publish a public Rules page before installing Sanity Check.")
            matches = Challenges.query.join(Tags).filter(Tags.value == MARKER).all()
            if len(matches) > 1:
                raise ValueError("Duplicate Sanity Check marker; review manually.")
            expected = dict(name=NAME, category="Misc", description=DESCRIPTION,
                            attribution="Yass1ir", value=50, type="standard", state="visible",
                            max_attempts=0, logic="any", requirements=None,
                            scheduled_at=None, module_id=None)
            if matches:
                challenge = matches[0]
                saved_flags = Flags.query.filter_by(challenge_id=challenge.id).all()
                if (any(getattr(challenge, key) != value for key, value in expected.items()) or
                        len(saved_flags) != 1 or saved_flags[0].content != flag or
                        saved_flags[0].type != "static" or saved_flags[0].data != ""):
                    raise ValueError("Existing Sanity Check was edited; refusing overwrite.")
            else:
                if Challenges.query.filter_by(name=NAME).first():
                    raise ValueError("Sanity Check name already exists outside this importer.")
                challenge = Challenges(**expected)
                db.session.add(challenge)
                db.session.flush()
                db.session.add(Flags(challenge_id=challenge.id, type="static", content=flag, data=""))
                for tag in ("Welcome", "Beginner", MARKER):
                    db.session.add(Tags(challenge_id=challenge.id, value=tag))
            if COMMENT_START in (page.content or ""):
                if page.content.count(COMMENT_START) != 1 or comment not in page.content:
                    raise ValueError("Rules source contains a different Sanity Check flag; refusing overwrite.")
            else:
                # Backups contain the original page; keep them beside the private
                # answer, never in the publicly downloadable upload directory.
                backup = answer_file.parent / ("rules-before-sanity-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
                backup.write_text(json.dumps({key: getattr(page, key) for key in
                    ("id", "route", "title", "content", "format", "draft", "hidden", "auth_required")},
                    ensure_ascii=False, indent=2), encoding="utf-8")
                page.content = (page.content or "").rstrip() + "\n\n" + comment + "\n"
            # Confirm that rendering preserves the comment before committing.
            if comment not in page.html:
                raise ValueError("Rules renderer removed or altered the flag comment.")
            notices = Notifications.query.filter_by(title=TITLE).all()
            if len(notices) > 1 or (notices and (notices[0].content != ANNOUNCEMENT or
                                               notices[0].user_id or notices[0].team_id)):
                raise ValueError("An edited announcement already uses this title.")
            if notices:
                notice = notices[0]
            else:
                notice = Notifications(title=TITLE, content=ANNOUNCEMENT)
                db.session.add(notice)
                created_notice = True
            db.session.commit()
            report = dict(id=challenge.id, name=challenge.name, value=challenge.value,
                          state=challenge.state, rules_url="/rules", notification_id=notice.id)
            notification_data = NotificationSchema().dump(notice).data
        except Exception:
            db.session.rollback()
            raise
        clear_pages()
        clear_challenges()
        if created_notice:
            notification_data.update(type="toast", sound=False)
            try:
                app.events_manager.publish(data=notification_data, type="notification")
            except Exception:
                app.logger.warning("Sanity Check announcement saved; live notification delivery failed.")
    print(json.dumps(report))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answer_file", type=Path)
    args = parser.parse_args()
    from CTFd import create_app
    publish(create_app(), args.answer_file)
