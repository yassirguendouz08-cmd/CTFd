"""Allowlisted challenge-only import of the supplied CTFd Bootcamp export.

Never restore an entire export: account/password/token/tracking tables are private.
Imported assets have separate records and never enter CTFd's public Files table.
"""
import hashlib
import io
import json
import re
import stat
import zipfile
from collections import defaultdict
from pathlib import PurePosixPath

from werkzeug.datastructures import FileStorage

from CTFd.models import db
from CTFd.utils.uploads import get_uploader

from .models import TrainingAnswer, TrainingAttachment, TrainingChallenge

# Reviewed offline exercises with the required attachment or in-description puzzle.
# Network services, event-only bonuses and incomplete exports stay unpublished.
READY = {3, 6, 8, 9, 11, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 32, 52, 55, 61, 63}
EASY = {3, 8, 9, 13, 32, 52, 61}
HARD = {4, 5, 6, 21, 23, 24, 29, 30, 40, 58, 60}
CATEGORIES = {"web": "Web", "crypto": "Cryptography", "forensics": "Forensics", "osint": "OSINT", "reverse": "Reverse Engineering", "pwn": "Pwn", "misc": "Misc", "bonnus": "Misc"}
REMOTE_IDS = {1, 2, 4, 5, 25, 26, 27, 28, 29, 30, 31, 35, 36, 37, 38, 39, 40, 56, 57, 58}


def safe_member(info):
    path = PurePosixPath(info.filename)
    if path.is_absolute() or ".." in path.parts or "\\" in info.filename or info.flag_bits & 1:
        raise ValueError("Unsafe or encrypted archive entry")
    if stat.S_ISLNK(info.external_attr >> 16):
        raise ValueError("Archive links are not accepted")
    if info.file_size > 32 * 1024 * 1024 or (info.compress_size and info.file_size > max(4 * 1024 * 1024, info.compress_size * 500)):
        raise ValueError("Archive expansion limit exceeded")


def player_attachment(name, data):
    """Remove organizer solutions from nested ZIPs without extracting or running code."""
    if not name.lower().endswith(".zip"):
        return data
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        if len(source.infolist()) > 1000 or sum(i.file_size for i in source.infolist()) > 64 * 1024 * 1024:
            raise ValueError("Nested archive expansion limit exceeded")
        for info in source.infolist():
            safe_member(info)
            filename = PurePosixPath(info.filename).name.lower()
            if re.search(r"(?:solve|solver|solution|writeup|walkthrough)", filename) or filename in {"flag.txt", "deploy.sh", "build.sh"}:
                continue
            # README/hints can be organizer material; keep only original challenge files.
            if filename.startswith("readme") or filename.startswith("hints"):
                continue
            target.writestr(info.filename, source.read(info))
    return output.getvalue()


def import_bootcamp(path):
    from . import digest
    uploaded, report = [], []
    uploader = get_uploader()
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 3000 or len({i.filename for i in infos}) != len(infos) or sum(i.file_size for i in infos) > 128 * 1024 * 1024:
            raise ValueError("Invalid or oversized challenge export")
        for info in infos:
            safe_member(info)

        def rows(name):
            raw = archive.read("db/" + name + ".json")
            return json.loads(raw)["results"] if raw else []

        challenges = rows("challenges")
        flags, files, hints = defaultdict(list), defaultdict(list), defaultdict(list)
        for row in rows("flags"):
            if row["type"] != "static" or row.get("data") not in (None, "", "case_insensitive"):
                raise ValueError("Only reviewed static flags are supported")
            if row.get("data") == "case_insensitive":
                raise ValueError("Case-insensitive flag needs explicit adaptation")
            flags[row["challenge_id"]].append(row["content"].strip())
        for row in rows("files"):
            if row.get("challenge_id"):
                location = row["location"]
                if not location.startswith("uploads/"):
                    location = "uploads/" + location
                files[row["challenge_id"]].append(location)
        for row in rows("hints"):
            hints[row["challenge_id"]].append(row["content"])

        # Validate and prepare everything before the first persistent mutation.
        prepared = []
        for row in challenges:
            cid = row["id"]
            if not flags[cid] or row.get("logic", "any") not in (None, "any"):
                raise ValueError("Missing flags or unsupported multi-flag logic")
            assets = [(PurePosixPath(name).name, player_attachment(name, archive.read(name))) for name in files[cid]]
            prepared.append((row, assets))
        try:
            for row, assets in prepared:
                cid = row["id"]; slug = f"bootcamp-2025-{cid}"
                item = TrainingChallenge.query.filter_by(slug=slug).first()
                if item:
                    # An import never overwrites an admin edit or existing progress.
                    report.append(item.active)
                    continue
                ready = cid in READY
                note = "" if ready else ("Restore an isolated lab before publication; historical endpoints have been removed." if cid in REMOTE_IDS else "Needs content review: external/event-only dependency or missing artifact.")
                description = row["description"].strip()
                if not ready:
                    description = re.sub(r"https?://[^\s<>]+|\bnc\s+[^\s]+\s+\d+", "[historical endpoint removed]", description)
                item = TrainingChallenge(slug=slug, name=row["name"].strip()[:120], category=CATEGORIES.get(row["category"].strip().lower(), "Misc"),
                    difficulty="Easy" if cid in EASY else "Hard" if cid in HARD else "Medium", kind="challenge",
                    description=description, hint="\n\n".join(hints[cid])[:4000], value=400 if cid in HARD else 50 if cid in EASY else 200,
                    minutes=90 if cid in HARD else 15 if cid in EASY else 40, active=ready,
                    flag_hash=digest("training:static:" + flags[cid][0]), source="CyberDune Bootcamp 2025" + (" · " + row["attribution"] if row.get("attribution") else ""), review_note=note)
                db.session.add(item); db.session.flush()
                for flag in flags[cid][1:]:
                    db.session.add(TrainingAnswer(challenge_id=item.id, flag_hash=digest("training:static:" + flag)))
                for name, data in assets:
                    location = uploader.upload(FileStorage(stream=io.BytesIO(data), filename=name), name)
                    uploaded.append(location)
                    db.session.add(TrainingAttachment(challenge_id=item.id, name=name, location=location, sha256=hashlib.sha256(data).hexdigest()))
                report.append(ready)
            db.session.commit()
        except Exception:
            db.session.rollback()
            for location in uploaded:
                uploader.delete(location)
            raise
    return dict(imported=len(report), published=sum(report), pending=len(report) - sum(report))
