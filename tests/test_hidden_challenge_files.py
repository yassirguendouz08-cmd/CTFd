"""Hidden challenge files must remain private even when a URL is known."""
import io
import tempfile

from werkzeug.datastructures import FileStorage

from CTFd.models import Challenges, db
from CTFd.utils import set_config
from CTFd.utils.security.signing import serialize
from CTFd.utils.uploads import upload_file
from tests.helpers import create_ctfd, destroy_ctfd, gen_challenge, login_as_user, register_user


def test_hidden_challenge_files_require_admin_including_signed_urls():
    app = create_ctfd()
    with tempfile.TemporaryDirectory() as folder:
        app.config["UPLOAD_FOLDER"] = folder
        try:
            with app.app_context():
                challenge = gen_challenge(db)
                challenge_id = challenge.id
                register_user(app)
                file = upload_file(
                    file=FileStorage(stream=io.BytesIO(b"private fixture"), filename="note.txt"),
                    type="challenge",
                    challenge_id=challenge_id,
                )
                path = "/files/" + file.location
                player_token = serialize({"user_id": 2, "team_id": None, "file_id": file.id})
                admin_token = serialize({"user_id": 1, "team_id": None, "file_id": file.id})
                guest = app.test_client()
                player = login_as_user(app)
                admin = login_as_user(app, "admin")

                set_config("challenge_visibility", "public")
                assert guest.get(path).status_code == 200
                assert player.get(path).status_code == 200

                challenge = Challenges.query.filter_by(id=challenge_id).one()
                challenge.state = "hidden"
                db.session.commit()
                assert guest.get(path).status_code == 404
                assert player.get(path).status_code == 404
                assert admin.get(path).status_code == 200

                set_config("challenge_visibility", "private")
                assert guest.get(path + "?token=" + player_token).status_code == 404
                assert guest.get(path + "?token=" + admin_token).status_code == 200

                challenge = Challenges.query.filter_by(id=challenge_id).one()
                challenge.state = "visible"
                db.session.commit()
                assert guest.get(path + "?token=" + player_token).status_code == 200
        finally:
            destroy_ctfd(app)
