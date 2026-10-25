"""Language switching must not modify flags, cached data, or hint access."""
from CTFd.cache import clear_challenges
from CTFd.models import Challenges, Flags, Hints, Solves, Fails
from CTFd.utils import set_config
from CTFd.utils.challenge_localization import catalog
from tests.helpers import (
    create_ctfd, destroy_ctfd, gen_challenge, gen_flag, gen_hint, gen_tag,
    gen_unlock, login_as_user, register_user,
)


def test_challenge_languages_follow_locale_without_mutating_sources():
    app = create_ctfd(ctf_theme="core-theme")
    try:
        with app.app_context():
            set_config("challenge_visibility", "public")
            set_config("hints_free_public_access", True)
            register_user(app)
            ids = {}
            for slug, translations in catalog().items():
                source = translations["fr"]
                chal = gen_challenge(app.db, name=source["name"], description=source["description"], value=100)
                gen_flag(app.db, chal.id, content="private-localization-test-flag")
                gen_tag(app.db, chal.id, value="bootcamp-first-steps:" + slug)
                gen_tag(app.db, chal.id, value="Débutant")
                hints = [gen_hint(app.db, chal.id, content=content, title=f"Indice {i}", cost=0).id
                         for i, content in enumerate(source["hints"], 1)]
                ids[slug] = (chal.id, hints)
            hidden = gen_challenge(app.db, name="Private exercise", state="hidden").id
            hidden_hint = gen_hint(app.db, hidden, content="Hidden clue").id
            clear_challenges()

        # Alternate on the same process/cache, including a return to English.
        for language in ("en", "fr", "ar", "en"):
            client = app.test_client()
            client.set_cookie("language", language, domain="localhost")
            listing = client.get("/api/v1/challenges?localized=1").get_json()["data"]
            by_id = {row["id"]: row for row in listing}
            assert hidden not in by_id
            for slug, (cid, hints) in ids.items():
                expected = catalog()[slug][language]
                assert by_id[cid]["name"] == expected["name"]
                assert by_id[cid]["tags"][-1]["value"] == {"en": "Beginner", "fr": "Débutant", "ar": "مبتدئ"}[language]
                detail = client.get(f"/api/v1/challenges/{cid}?localized=1").get_json()["data"]
                assert detail["name"] == expected["name"]
                assert detail["description"] == expected["description"]
                assert expected["name"] in detail["view"]
                assert "private-localization-test-flag" not in str(detail)
                for i, hid in enumerate(hints):
                    assert "content" not in detail["hints"][i]
                    hint = client.get(f"/api/v1/hints/{hid}?localized=1").get_json()["data"]
                    assert hint["content"] == expected["hints"][i]
                    assert hint["html"]
                raw = client.get(f"/api/v1/challenges/{cid}").get_json()["data"]
                assert raw["name"] == catalog()[slug]["fr"]["name"]
            assert client.get(f"/api/v1/challenges/{hidden}?localized=1").status_code == 404
            assert client.get(f"/api/v1/hints/{hidden_hint}?localized=1").status_code == 404

        cid, hints = ids["web-source"]
        with app.app_context():
            # Paid/locked hints must never gain content because of localization.
            Hints.query.get(hints[0]).cost = 10
            app.db.session.commit()
        with login_as_user(app) as player:
            locked = player.get(f"/api/v1/hints/{hints[0]}?localized=1").get_json()["data"]
            assert "content" not in locked and "html" not in locked
            with app.app_context():
                from CTFd.models import Users
                user = Users.query.filter_by(name="user").one()
                uid = user.id
                user.language = "ar"
                app.db.session.commit()
                gen_unlock(app.db, user_id=uid, target=hints[0])
            # User preference beats a conflicting cookie, as on every other page.
            from CTFd.cache import clear_user_session
            with app.app_context():
                clear_user_session(user_id=uid)
            player.set_cookie("language", "en", domain="localhost")
            response = player.get(f"/api/v1/challenges/{cid}?localized=1").get_json()["data"]
            assert response["name"] == catalog()["web-source"]["ar"]["name"]
            assert response["hints"][0]["content"] == catalog()["web-source"]["ar"]["hints"][0]

        with app.app_context():
            chal = Challenges.query.get(cid)
            chal.description = "Organizer edited this description."
            app.db.session.commit()
        client = app.test_client()
        client.set_cookie("language", "en", domain="localhost")
        edited = client.get(f"/api/v1/challenges/{cid}?localized=1").get_json()["data"]
        assert edited["description"] == "Organizer edited this description."
        with app.app_context():
            Challenges.query.get(cid).state = "hidden"
            app.db.session.commit()
            clear_challenges()
        with login_as_user(app, "admin") as admin:
            translated = admin.get(f"/api/v1/challenges/{cid}?localized=1").get_json()["data"]
            assert translated["name"] == catalog()["web-source"]["en"]["name"]
            canonical = admin.get(f"/api/v1/challenges/{cid}").get_json()["data"]
            assert canonical["name"] == catalog()["web-source"]["fr"]["name"]
        assert client.get(f"/api/v1/challenges/{cid}?localized=1").status_code == 404
        with app.app_context():
            for slug, (cid, hints) in ids.items():
                assert Challenges.query.get(cid).name == catalog()[slug]["fr"]["name"]
                assert Flags.query.filter_by(challenge_id=cid).one().content == "private-localization-test-flag"
                assert Hints.query.get(hints[1]).content == catalog()[slug]["fr"]["hints"][1]
            assert Solves.query.count() == Fails.query.count() == 0
    finally:
        destroy_ctfd(app)
