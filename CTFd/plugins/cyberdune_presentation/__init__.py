"""Opt-in event presentation. Never changes CTFd's competition or access rules."""
import json
import time
from datetime import datetime, timezone

from CTFd.utils import get_config


def presentation():
    try:
        settings = json.loads(get_config("theme_settings") or "{}")
    except (TypeError, ValueError):
        settings = {}
    if not isinstance(settings, dict):
        settings = {}
    result = {"mode": "platform", "status": "Platform ready"}
    if settings.get("cyberdune_mode") != "event":
        return result
    try:
        start, end = int(get_config("start")), int(get_config("end"))
        name = get_config("ctf_name")
        if not isinstance(name, str) or not name.strip() or start <= 0 or end <= start:
            return result
        start_date = datetime.fromtimestamp(start, timezone.utc).isoformat()
        end_date = datetime.fromtimestamp(end, timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return result
    now = time.time()
    status = "Starts soon" if now < start else "Event ended" if now >= end else "Event live"
    briefing = settings.get("cyberdune_event_briefing", "")
    result.update(mode="event", name=name.strip(), start=start, end=end,
                  start_date=start_date, end_date=end_date, status=status,
                  briefing=briefing if isinstance(briefing, str) else "")
    return result


def load(app):
    @app.context_processor
    def cyberdune_context():
        return {"CyberdunePresentation": presentation()}
