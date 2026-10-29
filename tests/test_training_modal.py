"""Training title migration and in-library challenge modal responses."""
from CTFd.models import Users, db
from CTFd.plugins.cyberdune_training import simplify_seeded_titles
from CTFd.plugins.cyberdune_training.models import TrainingChallenge, TrainingSolve
from tests.helpers import login_as_user
from tests.test_cyberdune_training import app, endpoint


def test_simple_example_title_migration_preserves_solves(app):
    with app.app_context():
        ecb = TrainingChallenge.query.filter_by(slug="pico-ecb-1").one()
        sql = TrainingChallenge.query.filter_by(slug="pico-sql-1").one()
        ecb.name = "picoCTF sample: ECB 1"
        ecb.source = "picoCTF official examples · Tim Becker / ForAllSecure · MIT · adapted by CyberDune"
        user_id = Users.query.filter_by(name="alice").one().id
        db.session.add(TrainingSolve(user_id=user_id, challenge_id=ecb.id, value=ecb.value))
        db.session.commit()

        simplify_seeded_titles()

        assert ecb.name == "ECB Challenge" and sql.name == "SQL Login"
        assert ecb.source.startswith("Licensed learning example")
        assert TrainingSolve.query.filter_by(challenge_id=ecb.id).count() == 1


def test_training_catalog_opens_challenge_modal_fragment(app):
    client = login_as_user(app, name="alice")
    catalog = client.get("/training")
    assert b"More practice" in catalog.data
    assert b"CyLab Security Academy / picoCTF" not in catalog.data
    assert b"data-training-open" in catalog.data
    assert b'<a class="tr-card' in catalog.data

    modal = client.get(endpoint("pico-ecb-1") + "?modal=1")
    assert modal.status_code == 200
    assert b"data-training-detail-fragment" in modal.data
    assert b"<h1>ECB Challenge</h1>" in modal.data

    direct = client.get(endpoint("pico-ecb-1"))
    assert direct.status_code == 200
    assert b"data-training-detail-fragment" in direct.data


def test_challenge_page_does_not_render_get_started_guide():
    from pathlib import Path

    template = Path("CTFd/themes/core-theme/templates/challenges.html").read_text()
    assert "cd-onboarding" not in template
    assert "cd-guide-restore" not in template
