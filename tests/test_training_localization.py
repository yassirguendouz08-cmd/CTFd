import hashlib
from html import unescape

from CTFd.plugins.cyberdune_training import challenge_text
from CTFd.plugins.cyberdune_training.models import TrainingChallenge
from tests.helpers import login_as_user
from tests.test_cyberdune_training import app


def test_imported_darija_challenge_copy_tracks_site_language_without_mutating_source(app, monkeypatch):
    source_name = "Original Darija title"
    source_description = "Original Darija challenge copy"
    with app.app_context():
        row = TrainingChallenge(
            slug="bootcamp-2025-3", name=source_name, category="Misc", difficulty="Easy",
            kind="challenge", description=source_description, hint="", value=50, minutes=15,
            active=True, flag_hash="private-test-digest", source="test fixture",
        )
        from CTFd.models import db
        db.session.add(row)
        db.session.commit()
        challenge_id = row.id

    monkeypatch.setitem(challenge_text.SOURCE_HASHES, "bootcamp-2025-3", {
        "name": hashlib.sha256(source_name.encode()).hexdigest(),
        "description": hashlib.sha256(source_description.encode()).hexdigest(),
    })
    client = login_as_user(app, name="alice")
    expected = {
        "en": ("Marlithor's Gift", "Decode the Base64 text below"),
        "fr": ("Le cadeau de Marlithor", "Décodez le texte Base64 ci-dessous"),
        "ar": ("هدية من Marlithor", "فكّ ترميز نص Base64 أدناه"),
    }
    for language, (title, description) in expected.items():
        monkeypatch.setattr(challenge_text, "get_locale", lambda language=language: language)
        response = client.get("/training/challenges/bootcamp-2025-3?modal=1")
        body = unescape(response.get_data(as_text=True))
        assert response.status_code == 200
        assert title in body and description in body

    with app.app_context():
        row = TrainingChallenge.query.get(challenge_id)
        assert row.name == source_name and row.description == source_description
        assert row.flag_hash == "private-test-digest"


def test_challenge_translation_stops_when_organizer_edits_source(app, monkeypatch):
    source_name = "Old title"
    changed_description = "Organizer's updated challenge briefing"
    with app.app_context():
        row = TrainingChallenge(
            slug="bootcamp-2025-8", name=source_name, category="Forensics", difficulty="Easy",
            kind="challenge", description=changed_description, hint="", value=50, minutes=15,
            active=True, flag_hash="private-test-digest", source="test fixture",
        )
        from CTFd.models import db
        db.session.add(row)
        db.session.commit()

    monkeypatch.setattr(challenge_text, "get_locale", lambda: "fr")
    client = login_as_user(app, name="alice")
    response = client.get("/training/challenges/bootcamp-2025-8?modal=1")
    body = unescape(response.get_data(as_text=True))
    assert response.status_code == 200
    assert changed_description in body
    assert "Welcome back to digital forensics" not in body
