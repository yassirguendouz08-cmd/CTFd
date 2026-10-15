"""Admins can review hidden exercises from the ordinary challenge board."""
from CTFd.cache import clear_challenges
from CTFd.models import Fails, Solves
from CTFd.utils import set_config
from tests.helpers import (
    create_ctfd, destroy_ctfd, gen_challenge, gen_flag, login_as_user, register_user,
)


def test_admin_board_includes_hidden_without_exposing_them_to_players():
    app = create_ctfd(ctf_theme="core-theme")
    try:
        with app.app_context():
            visible_id = gen_challenge(app.db, name="Published exercise").id
            hidden_id = gen_challenge(app.db, name="Private exercise", state="hidden").id
            gen_flag(app.db, challenge_id=hidden_id, content="private-test-answer")
            set_config("challenge_visibility", "public")
            register_user(app)
            clear_challenges()

        with login_as_user(app, "admin") as admin:
            response = admin.get("/api/v1/challenges")
            assert response.status_code == 200
            entries = {row["id"]: row for row in response.get_json()["data"]}
            assert set(entries) == {visible_id, hidden_id}
            assert entries[hidden_id]["state"] == "hidden"
            assert entries[visible_id]["state"] == "visible"
            assert admin.get(f"/api/v1/challenges/{hidden_id}").status_code == 200
            board = admin.get("/challenges").get_data(as_text=True)
            assert "Hidden · admins only" in board
            for submission, expected in (("private-test-answer", "correct"), ("wrong", "incorrect")):
                result = admin.post("/api/v1/challenges/attempt", json={
                    "challenge_id": hidden_id, "submission": submission,
                })
                assert result.status_code == 200
                assert result.get_json()["data"]["status"] == expected

        for client in (app.test_client(), login_as_user(app)):
            for url in ("/api/v1/challenges", "/api/v1/challenges?view=admin"):
                result = client.get(url)
                assert result.status_code == 200
                assert [row["id"] for row in result.get_json()["data"]] == [visible_id]
            assert client.get(f"/api/v1/challenges/{hidden_id}").status_code == 404
            assert "Hidden · admins only" not in client.get("/challenges").get_data(as_text=True)

        with app.app_context():
            assert Solves.query.count() == 0
            assert Fails.query.count() == 0
    finally:
        destroy_ctfd(app)
