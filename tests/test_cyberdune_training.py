"""Independent training behavior, authorization, fairness and exercise artifacts."""
import ast
import base64
import csv
import io
import json
import struct
import tarfile
import zipfile
import zlib
from datetime import datetime, timedelta

import pytest
from PIL import Image

from CTFd.config import TestingConfig
from CTFd.models import Challenges, Solves, Submissions, Users, db
from CTFd.plugins.cyberdune_training import exercise_flag, remove_legacy_browser_labs, seed_starters, upgrade_intermediate_starters, upgrade_yassir_gift, user_summary
from CTFd.plugins.cyberdune_training.catalog import CATEGORIES
from CTFd.plugins.cyberdune_training.models import TrainingAnswer, TrainingAttempt, TrainingChallenge, TrainingSolve
from CTFd.utils import set_config
from tests.helpers import create_ctfd, destroy_ctfd, gen_team, gen_user, login_as_user


class TrainingConfig(TestingConfig):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SERVER_NAME = None


@pytest.fixture
def app():
    application = create_ctfd(enable_plugins=True, config=TrainingConfig, ctf_theme="core-theme")
    with application.app_context():
        gen_user(db, name="alice", email="alice@example.test")
        gen_user(db, name="bob", email="bob@example.test")
        gen_user(db, name="charlie", email="charlie@example.test")
    yield application
    destroy_ctfd(application)


def solution(app, slug, username="alice"):
    with app.app_context():
        return exercise_flag(TrainingChallenge.query.filter_by(slug=slug).one(), Users.query.filter_by(name=username).one().id)


def endpoint(slug="base64-trail"):
    return "/training/challenges/" + slug


def nonce(client):
    with client.session_transaction() as session:
        return session["nonce"]


def test_starter_library_and_independent_event_access(app):
    with app.app_context():
        assert TrainingChallenge.query.count() == 40
        assert TrainingChallenge.query.filter_by(active=True).count() == 40
        assert {row.category for row in TrainingChallenge.query.all()} == set(CATEGORIES)
        assert TrainingChallenge.query.filter_by(kind="lab", active=True).count() == 0
        seed_starters()
        assert TrainingChallenge.query.count() == 40
        set_config("start", 9999999999)
        set_config("end", 10000000999)
    client = app.test_client()
    assert client.get("/training").status_code == 200
    assert b"Academy leaderboard" in client.get("/training").data
    assert b"/academy" in client.get("/").data
    assert b"No Academy flags captured yet" in client.get("/training/scoreboard").data
    assert client.get("/academy").status_code == 200
    assert client.get("/academy/scoreboard").status_code == 200
    assert b"XP" not in client.get("/academy").data
    assert b"XP" not in client.get("/academy/scoreboard").data


def test_intermediate_starter_migration_preserves_organizer_edits(app):
    with app.app_context():
        dispatch = TrainingChallenge.query.filter_by(slug="base64-trail").one()
        custom = TrainingChallenge.query.filter_by(slug="source-review").one()
        dispatch.description = "An intercepted fictional dispatch uses a common text encoding. Download and decode it to recover your flag."
        dispatch.hint = "The alphabet and trailing equals signs suggest Base64. Encoding is not encryption."
        dispatch.difficulty = "Easy"; dispatch.minutes = 10
        custom.description = "Organizer's edited copy"
        set_config("cyberdune_training:intermediate_starters_v2", False)
        assert upgrade_intermediate_starters() == 1
        assert dispatch.difficulty == "Medium" and dispatch.minutes == 30 and dispatch.value == 200 and dispatch.hint == ""
        assert "repeating XOR" in dispatch.description and custom.description == "Organizer's edited copy"


def test_yassir_gift_migration_replaces_static_answer_with_generated_recipe(app):
    with app.app_context():
        gift = TrainingChallenge(slug="bootcamp-2025-3", name="cadeau hada mn 3and marlithor_cyber",
            category="Cryptography", difficulty="Easy", kind="challenge", description="old", hint="",
            value=50, minutes=10, active=True, recipe=None, flag_hash="old-hash")
        db.session.add(gift); db.session.flush()
        db.session.add(TrainingAnswer(challenge_id=gift.id, flag_hash="another-old-hash")); db.session.commit()
        set_config("cyberdune_training:yassir_gift_crypto_v1", False)
        assert upgrade_yassir_gift() is True
        assert gift.name == "Yassir's Gift" and gift.difficulty == "Medium" and gift.recipe == "yassir-gift"
        assert gift.flag_hash is None and TrainingAnswer.query.filter_by(challenge_id=gift.id).count() == 0


def test_search_filters_and_empty_recovery(app):
    client = app.test_client()
    response = client.get("/training?category=Linux&kind=challenge")
    assert b"Hidden Backup" in response.data and b"Find your way around" not in response.data
    response = client.get("/training?q=not-an-existing-exercise")
    assert b"No exercises match" in response.data and b"Clear filters" in response.data
    assert b"No exercises match" in client.get("/training?q=%25").data
    assert client.get("/training?page=bad").status_code == 200


def test_legacy_browser_labs_are_permanently_removed_with_history(app):
    with app.app_context():
        user = Users.query.filter_by(name="alice").one()
        legacy = []
        for slug in ("header-lab", "rot13-lab", "logs-lab", "archive-lab", "bytecode-lab", "stack-lab", "terminal-lab", "reassembly-lab", "pattern-lab"):
            challenge = TrainingChallenge(slug=slug, name=slug, category="Misc", difficulty="Medium", kind="lab",
                description="Old lab", hint="", value=100, minutes=20, active=True, recipe=slug)
            db.session.add(challenge); db.session.flush(); legacy.append(challenge)
            db.session.add(TrainingSolve(user_id=user.id, challenge_id=challenge.id, value=challenge.value))
            db.session.add(TrainingAttempt(user_id=user.id, challenge_id=challenge.id, correct=False))
            db.session.add(TrainingAnswer(challenge_id=challenge.id, flag_hash="test-hash"))
        db.session.commit()
        legacy_ids = [item.id for item in legacy]
        legacy_slugs = [item.slug for item in legacy]

        deleted = remove_legacy_browser_labs()

        assert deleted == 9
        assert TrainingChallenge.query.filter(TrainingChallenge.slug.in_(legacy_slugs)).count() == 0
        assert TrainingSolve.query.filter(TrainingSolve.challenge_id.in_(legacy_ids)).count() == 0
        assert TrainingAttempt.query.filter(TrainingAttempt.challenge_id.in_(legacy_ids)).count() == 0
        assert TrainingAnswer.query.filter(TrainingAnswer.challenge_id.in_(legacy_ids)).count() == 0
        assert TrainingChallenge.query.filter_by(kind="lab").count() == 0


def test_guests_cannot_get_artifacts_labs_or_submit(app):
    client = app.test_client()
    for path in [endpoint(), endpoint() + "/artifact", endpoint("response-header") + "/artifact"]:
        response = client.get(path)
        assert response.status_code == 302 and "/login" in response.location
    assert client.post(endpoint() + "/submit", data=json.dumps({"flag": "x"}), content_type="application/json").status_code == 403


def test_training_solve_never_changes_ctf_or_team_score(app):
    with app.app_context():
        team = gen_team(db); alice = Users.query.filter_by(name="alice").one(); bob = Users.query.filter_by(name="bob").one()
        alice.team_id = team.id; bob.team_id = team.id; set_config("user_mode", "teams"); db.session.commit()
        before = (Challenges.query.count(), Solves.query.count(), Submissions.query.count(), team.get_score())
    client = login_as_user(app, name="alice")
    flag = solution(app, "base64-trail")
    response = client.post(endpoint() + "/submit", json={"flag": flag})
    assert response.status_code == 200 and response.json["status"] == "correct"
    assert response.json["summary"]["solved"] == 1
    assert "xp" not in response.json["summary"]
    assert response.json["summary"]["rank"] == 1
    with app.app_context():
        team = Users.query.filter_by(name="alice").one().team
        assert (Challenges.query.count(), Solves.query.count(), Submissions.query.count(), team.get_score()) == before
        assert user_summary(Users.query.filter_by(name="bob").one())["solved"] == 0
        assert TrainingSolve.query.count() == 1
    assert b"The encoded dispatch" in client.get("/training?progress=solved").data
    assert b"The encoded dispatch" not in client.get("/training?progress=unsolved").data


def test_duplicate_solves_do_not_inflate_board(app):
    client = login_as_user(app, name="alice"); flag = solution(app, "base64-trail")
    assert client.post(endpoint() + "/submit", json={"flag": flag}).json["status"] == "correct"
    for _ in range(3):
        assert client.post(endpoint() + "/submit", json={"flag": flag}).json["status"] == "already_solved"
    with app.app_context():
        assert TrainingSolve.query.count() == 1 and TrainingAttempt.query.count() == 1


def test_flags_belong_to_each_player(app):
    client = login_as_user(app, name="bob")
    other = solution(app, "base64-trail", "alice"); own = solution(app, "base64-trail", "bob")
    assert other != own
    assert client.post(endpoint() + "/submit", json={"flag": other}).json["status"] == "incorrect"
    assert client.post(endpoint() + "/submit", json={"flag": own}).json["status"] == "correct"


def test_rank_uses_solve_count_and_equal_counts_share_place(app):
    with app.app_context():
        a, b, c = [Users.query.filter_by(name=name).one() for name in ("alice", "bob", "charlie")]
        first, second = TrainingChallenge.query.limit(2).all()
        for user, exercise, value in [(a, first, 5), (a, second, 5), (b, first, 900), (b, second, 900), (c, first, 9999)]:
            db.session.add(TrainingSolve(user_id=user.id, challenge_id=exercise.id, value=value))
        db.session.commit()
        assert user_summary(a)["rank"] == 1 and user_summary(b)["rank"] == 1
        assert user_summary(c)["rank"] == 3
    response = app.test_client().get("/training/scoreboard")
    text = response.get_data(as_text=True)
    assert text.index("alice") < text.index("bob") < text.index("charlie")
    assert "alice@example.test" not in text


def test_hidden_banned_and_admin_accounts_are_not_publicly_ranked(app):
    with app.app_context():
        exercise = TrainingChallenge.query.first()
        for name in ("alice", "bob", "admin"):
            user = Users.query.filter_by(name=name).one()
            db.session.add(TrainingSolve(user_id=user.id, challenge_id=exercise.id, value=50))
            if name == "alice": user.hidden = True
            if name == "bob": user.banned = True
        db.session.commit()
    assert b"No Academy flags captured yet" in app.test_client().get("/training/scoreboard").data


def test_unpublished_exercise_is_not_accessible_and_history_is_retained(app):
    client = login_as_user(app, name="alice")
    client.post(endpoint() + "/submit", json={"flag": solution(app, "base64-trail")})
    with app.app_context():
        TrainingChallenge.query.filter_by(slug="base64-trail").one().active = False
        db.session.commit()
    for path in [endpoint(), endpoint() + "/artifact"]:
        assert client.get(path).status_code == 404
    assert client.post(endpoint() + "/submit", json={"flag": "x"}).status_code == 404
    assert b"No Academy flags captured yet" in client.get("/training/scoreboard").data
    with app.app_context(): assert TrainingSolve.query.count() == 1


def test_csrf_cannot_be_bypassed_with_an_authorization_header(app):
    client = login_as_user(app, name="alice")
    response = client.post(endpoint() + "/submit", data=json.dumps({"flag": solution(app, "base64-trail")}), content_type="application/json", headers={"Authorization": "Bearer invalid"})
    assert response.status_code in (401, 403)
    with app.app_context(): assert TrainingSolve.query.count() == 0


@pytest.mark.parametrize("flag", [None, 12, [], "", " " * 2, "x" * 257])
def test_invalid_flag_payloads_are_rejected(app, flag):
    client = login_as_user(app, name="alice")
    assert client.post(endpoint() + "/submit", json={"flag": flag}).status_code == 400


def test_unicode_wrong_flag_and_request_limit(app):
    client = login_as_user(app, name="alice")
    assert client.post(endpoint() + "/submit", json={"flag": "العلم"}).json["status"] == "incorrect"
    assert client.post(endpoint() + "/submit", json={"flag": "x" * 5000}).status_code == 413
    for _ in range(29): assert client.post(endpoint() + "/submit", json={"flag": "wrong"}).status_code == 200
    response = client.post(endpoint() + "/submit", json={"flag": "wrong"})
    assert response.status_code == 429 and response.headers["Retry-After"] == "60"


def test_required_email_verification_also_covers_training(app):
    client = login_as_user(app, name="alice")
    with app.app_context(): set_config("verify_emails", True)
    assert "/confirm" in client.get(endpoint() + "/artifact").location
    assert "/confirm" in client.get(endpoint("response-header") + "/artifact").location
    assert client.post(endpoint() + "/submit", json={"flag": "x"}).status_code == 403


def test_every_starter_download_is_solvable_and_private(app):
    client = login_as_user(app, name="alice")
    for slug in ["source-review", "base64-trail", "image-metadata", "public-trail", "xor-blueprint", "endian-note", "hidden-files", "packet-courier", "archive-layers"]:
        response = client.get(endpoint(slug) + "/artifact"); data = response.data; flag = solution(app, slug)
        assert response.status_code == 200 and "no-store" in response.headers["Cache-Control"]
        if slug == "source-review":
            import codecs
            recovered = codecs.decode(data.decode().split("audit-note: ")[1].split(" -->")[0], "rot_13")
        elif slug == "base64-trail":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                delivery = next(row for row in csv.DictReader(io.StringIO(archive.read("delivery-log.csv").decode())) if row["delivery_id"] == "D-204" and row["recipient"] == "node-7" and row["status"] == "accepted")
                envelopes = [json.loads(row)["envelope_b64"] for row in archive.read("envelopes.jsonl").splitlines()]
                envelope = next(json.loads(base64.b64decode(item)) for item in envelopes if json.loads(base64.b64decode(item))["record_id"] == delivery["delivery_id"])
                key = json.loads(archive.read("keyring.json"))[envelope["key_id"]].encode()
                cipher = bytes.fromhex(envelope["ciphertext_hex"])
                recovered_bytes = bytes(value ^ key[index % len(key)] for index, value in enumerate(cipher))
                assert f"{zlib.crc32(recovered_bytes) & 0xffffffff:08x}" == envelope["crc32"]
                recovered = recovered_bytes.decode()
        elif slug == "image-metadata":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                acquisition = Image.open(io.BytesIO(archive.read("evidence.png"))).info["Acquisition-ID"]
                records = json.loads(archive.read("chain-of-custody.json"))
                record = next(row for row in records if row["acquisition_id"] == acquisition and row["state"] == "verified")
                key = json.loads(archive.read("keyring.json"))[record["key_id"]].encode()
                cipher = bytes.fromhex(record["ciphertext_hex"])
                recovered_bytes = bytes(value ^ key[index % len(key)] for index, value in enumerate(cipher))
                assert f"{zlib.crc32(recovered_bytes) & 0xffffffff:08x}" == record["crc32"]
                recovered = recovered_bytes.decode()
        elif slug == "public-trail":
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                profile = json.loads(z.read("profiles/dune.json"))
                envelope = json.loads(base64.b64decode(profile["archive_note"]))
                key = json.loads(z.read("keyring.json"))[envelope["key_id"]].encode()
                cipher = bytes.fromhex(envelope["ciphertext_hex"])
                recovered_bytes = bytes(value ^ key[index % len(key)] for index, value in enumerate(cipher))
                assert f"{zlib.crc32(recovered_bytes) & 0xffffffff:08x}" == envelope["crc32"]
                recovered = recovered_bytes.decode()
        elif slug == "xor-blueprint": recovered = bytes(v ^ 42 for v in ast.literal_eval(ast.parse(data.decode()).body[0].value)).decode()
        elif slug == "endian-note":
            assert data[:4] == b"MEM1"
            length = struct.unpack("<H", data[4:6])[0]
            key = data[6]
            recovered = bytes(value ^ key for value in data[7:7 + length]).decode()
        elif slug == "hidden-files":
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                assert all(not name.startswith("/") and ".." not in name.split("/") for name in archive.getnames())
                manifest = json.load(archive.extractfile("workspace/manifest.json"))
                encoded = archive.extractfile("workspace/" + manifest["receipt"]).read()
                cipher = bytes.fromhex(base64.b64decode(encoded).decode())
                key = json.load(archive.extractfile("workspace/.config/keys.json"))[manifest["key_id"]].encode()
                recovered_bytes = bytes(value ^ key[index % len(key)] for index, value in enumerate(cipher))
                expected_crc = archive.extractfile("workspace/.config/nightly-07/receipt.crc32").read().decode().strip()
                assert f"{zlib.crc32(recovered_bytes) & 0xffffffff:08x}" == expected_crc
                recovered = recovered_bytes.decode()
        elif slug == "packet-courier":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                capture = archive.read("capture.pcap")
                keyring = json.loads(archive.read("keyring.json"))
                offset, fragments, session_meta = 24, {}, None
                while offset < len(capture):
                    _, _, captured, _ = struct.unpack_from("<IIII", capture, offset)
                    frame = capture[offset + 16:offset + 16 + captured]; offset += 16 + captured
                    ip_offset = 14; udp_offset = ip_offset + (frame[ip_offset] & 0x0f) * 4
                    _, dest_port, _, _ = struct.unpack_from("!HHHH", frame, udp_offset)
                    if dest_port != 31337: continue
                    fields = dict(part.split("=", 1) for part in frame[udp_offset + 8:].decode().split(";"))
                    if fields["sid"] != "S-42": continue
                    sequence, total = map(int, fields["seq"].split("/"))
                    fragments[sequence] = bytes.fromhex(fields["hex"])
                    session_meta = fields
                assert len(fragments) == total == 3
                cipher = b"".join(fragments[index] for index in range(1, total + 1))
                key = keyring[session_meta["kid"]].encode()
                recovered_bytes = bytes(value ^ key[index % len(key)] for index, value in enumerate(cipher))
                assert f"{zlib.crc32(recovered_bytes) & 0xffffffff:08x}" == session_meta["crc"]
                recovered = recovered_bytes.decode()
        else:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                manifest = json.loads(z.read("manifest.json"))
                cipher = base64.b64decode(bytes.fromhex(z.read(manifest["payload"]).decode()))
                key = z.read(manifest["xor_key"]).strip()
                recovered_bytes = bytes(value ^ key[index % len(key)] for index, value in enumerate(cipher))
                assert f"{zlib.crc32(recovered_bytes) & 0xffffffff:08x}" == manifest["crc32"]
                recovered = recovered_bytes.decode()
        assert recovered == flag
        assert client.post(endpoint(slug) + "/submit", json={"flag": recovered}).json["status"] == "correct"


def test_legacy_browser_lab_routes_and_records_are_gone(app):
    client = login_as_user(app, name="alice")
    old_slugs = ["header-lab", "rot13-lab", "logs-lab", "archive-lab", "bytecode-lab", "stack-lab", "terminal-lab", "reassembly-lab", "pattern-lab"]
    for slug in old_slugs:
        assert client.get(endpoint(slug)).status_code == 404
        assert client.get(endpoint(slug) + "/lab").status_code == 404
    with app.app_context():
        assert TrainingChallenge.query.filter_by(kind="lab").count() == 0


def test_admin_can_manage_static_content_without_leaking_flags(app):
    admin = login_as_user(app, name="admin")
    values = {"nonce": nonce(admin), "name": "Custom practice", "category": "Web", "difficulty": "Hard", "kind": "challenge", "description": "Find the answer. <script>alert(1)</script>", "hint": "A free hint", "value": "200", "minutes": "25", "flag": "TRAIN{private-answer}", "active": "1"}
    response = admin.post("/admin/training", data=values)
    assert response.status_code == 302
    assert b"TRAIN{private-answer}" not in admin.get(response.location).data
    with app.app_context():
        item = TrainingChallenge.query.filter_by(name="Custom practice").one();slug = item.slug; item_id = item.id
        assert item.flag_hash and item.flag_hash != values["flag"]
    client = login_as_user(app, name="alice")
    assert b"<script>alert(1)</script>" not in client.get(endpoint(slug)).data
    assert client.post(endpoint(slug) + "/submit", json={"flag": values["flag"]}).json["status"] == "correct"
    assert client.get("/admin/training").status_code in (302, 403)
    assert admin.post(f"/admin/training/{item_id}", data={"nonce":nonce(admin), "action":"toggle"}).status_code == 302
    assert client.get(endpoint(slug)).status_code == 404


def test_admin_can_hide_and_restore_the_entire_academy(app):
    admin = login_as_user(app, name="admin")
    assert b"Hide Academy" in admin.get("/admin/training").data
    assert admin.post("/admin/training", data={"nonce": nonce(admin), "action": "toggle_academy_visibility"}).status_code == 302
    assert b"Show Academy" in admin.get("/admin/training").data
    assert b"/academy" not in admin.get("/").data
    for path in ("/academy", "/training", "/training/scoreboard", "/academy/scoreboard", "/academy/challenges/base64-trail", "/academy/challenges/base64-trail/artifact"):
        assert admin.get(path).status_code == 404
    assert admin.post("/admin/training", data={"nonce": nonce(admin), "action": "toggle_academy_visibility"}).status_code == 302
    assert admin.get("/academy").status_code == 200
    assert b"/academy" in admin.get("/").data


def test_admin_rejects_unusable_labs_and_unsafe_urls(app):
    admin = login_as_user(app, name="admin")
    values = {"nonce":nonce(admin), "name":"Unsafe lab", "category":"Web", "difficulty":"Easy", "kind":"lab", "description":"A test.", "value":"10", "minutes":"10", "flag":"flag", "resource_url":"javascript:alert(1)"}
    assert admin.post("/admin/training", data=values).status_code == 400
    values["resource_url"] = ""
    assert admin.post("/admin/training", data=values).status_code == 400
    with app.app_context(): assert TrainingChallenge.query.count() == 40


def test_attempt_pruning_never_removes_solve_history(app):
    client = login_as_user(app, name="alice")
    client.post(endpoint() + "/submit", json={"flag":solution(app,"base64-trail")})
    with app.app_context():
        TrainingAttempt.query.first().created = datetime.utcnow() - timedelta(days=40); db.session.commit()
    result = app.test_cli_runner().invoke(args=["training", "prune-attempts", "--days", "30"])
    assert result.exit_code == 0
    with app.app_context(): assert TrainingSolve.query.count() == 1 and TrainingAttempt.query.count() == 0
