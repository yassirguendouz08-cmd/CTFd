"""Academy modal behavior and permanent removal of third-party examples."""
from CTFd.models import Users, db
from CTFd.plugins.cyberdune_training.models import TrainingChallenge, TrainingSolve
from tests.helpers import login_as_user
from tests.test_cyberdune_training import app, endpoint


def test_pico_challenges_are_removed_from_catalog_and_routes(app):
    client = login_as_user(app, name="alice")
    with app.app_context():
        assert TrainingChallenge.query.filter(TrainingChallenge.slug.in_(("pico-ecb-1", "pico-sql-1"))).count() == 0
    catalog = client.get("/academy")
    assert b"picoCTF" not in catalog.data
    for slug in ("pico-ecb-1", "pico-sql-1"):
        assert client.get(endpoint(slug)).status_code == 404
        assert client.get(endpoint(slug) + "/artifact").status_code == 404


def test_training_catalog_opens_challenge_modal_fragment(app):
    client = login_as_user(app, name="alice")
    catalog = client.get("/training")
    assert b"More practice" not in catalog.data
    assert b"learn.cylabacademy.org/library" not in catalog.data
    assert b"primer.cylabacademy.org" not in catalog.data
    assert b"data-training-open" in catalog.data
    assert b'<a class="tr-card' in catalog.data
    assert b'modal-content cyber-theme tr-training-modal' in catalog.data
    assert b'data-training-dialog-title' in catalog.data

    modal = client.get(endpoint("field-notes") + "?modal=1")
    assert modal.status_code == 200
    assert b"data-training-detail-fragment" in modal.data
    assert b'data-training-challenge-title="Field Notes"' in modal.data
    assert b"tr-modal-meta" in modal.data
    assert b"tr-stats" not in modal.data
    assert b"Independent from the CTF scoreboard" not in modal.data

    direct = client.get(endpoint("field-notes"))
    assert direct.status_code == 200
    assert b"data-training-detail-fragment" in direct.data


def test_academy_cards_show_points_and_live_solve_totals(app):
    client = login_as_user(app, name="alice")
    catalog = client.get("/academy")
    assert b"tr-card-points" in catalog.data
    assert b"data-count=\"0\"" in catalog.data
    assert b'data-solve-count>0</strong><span>solves</span>' in catalog.data

    with app.app_context():
        challenge = TrainingChallenge.query.filter_by(slug="source-review").one()
        user = Users.query.filter_by(name="alice").one()
        db.session.add(TrainingSolve(user_id=user.id, challenge_id=challenge.id, value=challenge.value))
        db.session.commit()
        points = challenge.value

    catalog = client.get("/academy")
    assert f">{points}</strong>".encode() in catalog.data
    assert b"data-count=\"1\"" in catalog.data
    assert b'data-solve-count>1</strong><span>solve</span>' in catalog.data
