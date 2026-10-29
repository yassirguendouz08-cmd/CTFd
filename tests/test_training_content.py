"""Recover advanced flags from player evidence, without reading generator state."""
import gzip
import hashlib
import io
import json
import math
import struct
import zipfile

import pytest
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from CTFd.models import Users, db
from CTFd.plugins.cyberdune_training import exercise_flag
from CTFd.plugins.cyberdune_training.bootcamp import import_bootcamp
from CTFd.plugins.cyberdune_training.models import TrainingAnswer, TrainingAttachment, TrainingChallenge, TrainingSolve
from tests.helpers import login_as_user
from tests.test_cyberdune_training import app, endpoint, solution


@pytest.mark.parametrize("slug", ["fault-line", "dune-vm", "clock-drift", "pico-ecb-1"])
def test_advanced_and_pico_artifacts_have_working_independent_solutions(app, slug):
    client = login_as_user(app, name="alice")
    response = client.get(endpoint(slug) + "/artifact")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert not any(word in name.lower() for name in archive.namelist() for word in ("solve.py", "writeup"))
        if slug == "fault-line":
            audit = json.loads(archive.read("audit.json")); n = int(audit["n"])
            factor = math.gcd(pow(int(audit["faulty_signature"]), audit["e"], n) - int(audit["digest"]), n)
            assert 1 < factor < n and n % factor == 0
            assert pow(int(audit["signature"]), audit["e"], n) == int(audit["digest"])
            key = hashlib.sha256(b"cyberdune-hsm-v1:" + min(factor, n // factor).to_bytes(128, "big") + bytes.fromhex(audit["instance"])).digest()
            recovered = AESGCM(key).decrypt(bytes.fromhex(audit["nonce"]), archive.read("sealed.bin"), audit["instance"].encode()).decode()
        elif slug == "dune-vm":
            data = archive.read("target.bin"); r = list(struct.unpack("<" + "Q" * (len(data) // 8), data)); mask = (1 << 64) - 1
            for op, a, b, k in reversed(list(struct.iter_unpack("<BBBQ", archive.read("program.bin")))):
                if op == 1: r[a] = (r[a] - k) & mask
                elif op == 2: r[a] ^= k
                elif op == 3: r[a] = (r[a] * pow(k, -1, 1 << 64)) & mask
                elif op == 4: r[a] = ((r[a] >> k) | (r[a] << (64 - k))) & mask
                else: r[a] ^= r[b]
            original = struct.pack("<" + "Q" * len(r), *r); recovered = original[1:1 + original[0]].decode()
        elif slug == "clock-drift":
            incident = json.loads(archive.read("incident.json")); clocks = incident["clocks"]
            auth = [json.loads(line) for line in gzip.decompress(archive.read("auth.jsonl.gz")).splitlines()]
            edge = [json.loads(line) for line in gzip.decompress(archive.read("edge.jsonl.gz")).splitlines()]
            frames = list(struct.iter_unpack("<IIB32H", archive.read("shares.bin")))
            shares = {}
            for event in auth:
                if event["label"] != incident["label"] or event["role"] != "recovery" or event["result"] != "allow": continue
                t = event["t"] - clocks["auth"]
                acks = [e for e in edge if e["session_id"] == event["session_id"] and abs(e["t"] - clocks["edge"] - t) <= 2]
                for sid, ts, x, *values in frames:
                    if sid == event["session_id"] and abs(ts - clocks["capture"] - t) <= 2 and any(a["share_x"] == x for a in acks): shares[x] = values
            assert len(shares) == 3
            key = bytes(sum(values[i] * math.prod((-other * pow(x - other, -1, 257)) % 257 for other in shares if other != x) for x, values in shares.items()) % 257 for i in range(32))
            recovered = AESGCM(key).decrypt(bytes.fromhex(incident["nonce"]), archive.read("sealed.bin"), incident["label"].encode()).decode()
        else:
            export = json.loads(archive.read("service-export.json"))
            decoder = Cipher(algorithms.AES(bytes.fromhex(export["key"])), modes.ECB()).decryptor()
            padded = decoder.update(bytes.fromhex(export["ciphertext"])) + decoder.finalize()
            unpadder = padding.PKCS7(128).unpadder(); recovered = (unpadder.update(padded) + unpadder.finalize()).decode()
            assert "MIT" in archive.read("LICENSE-picoCTF.txt").decode()
    assert recovered == solution(app, slug)
    assert client.post(endpoint(slug) + "/submit", json={"flag": recovered}).json["status"] == "correct"
    other = login_as_user(app, name="bob")
    assert other.post(endpoint(slug) + "/submit", json={"flag": recovered}).json["status"] == "incorrect"


def test_sql_example_reproduces_injection_without_accessing_real_tables_or_files(app):
    client = login_as_user(app, name="alice"); path = endpoint("pico-sql-1") + "/sql"
    assert client.post(path, json={"username":"nobody", "password":"wrong"}).json["success"] is False
    response = client.post(path, json={"username":"' OR 1=1 --", "password":""})
    assert response.json["message"] == solution(app, "pico-sql-1")
    for payload in ["' UNION SELECT name, sql FROM sqlite_master --", "' UNION SELECT load_extension('/tmp/x'), 'x' --", "'; ATTACH DATABASE '/tmp/test' AS bad; --", "' UNION SELECT readfile('/etc/passwd'), 'x' --"]:
        assert client.post(path, json={"username":payload, "password":""}).json["success"] is False
    assert client.post(path, json={"username": [], "password":"x"}).status_code == 400
    with app.app_context():
        assert Users.query.count() == 4 and TrainingSolve.query.count() == 0
    assert app.test_client().post(path, json={"username":"x", "password":"x"}).status_code == 403


def sample_export(path, malicious=False):
    with zipfile.ZipFile(path, "w") as archive:
        def table(name, rows): archive.writestr("db/" + name + ".json", json.dumps(dict(results=rows)))
        table("challenges", [dict(id=3, name="Sample", category="Crypto", description="Decode the attachment.", logic="any"), dict(id=57, name="Pending lab", category="WEB ", description="Old instance http://192.0.2.8:8000/", logic="any")])
        table("flags", [dict(challenge_id=3, type="static", content="secret-one", data=""), dict(challenge_id=3, type="static", content="secret-two", data=""), dict(challenge_id=57, type="static", content="private-lab", data="")])
        table("hints", []); table("files", [dict(challenge_id=3, location="sample/clue.txt")])
        table("users", [dict(name="private-original-user", password="never-import-this")])
        archive.writestr("uploads/sample/clue.txt", b"a fictional exercise artifact")
        if malicious: archive.writestr("../outside.txt", "bad")


def test_bootcamp_import_is_independent_idempotent_and_keeps_assets_authenticated(app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    archive = tmp_path / "pack.zip"; sample_export(archive)
    with app.app_context():
        report = import_bootcamp(archive); assert report == dict(imported=2, published=1, pending=1)
        import_bootcamp(archive)
        assert TrainingChallenge.query.count() == 25 and TrainingAttachment.query.count() == 1 and TrainingAnswer.query.count() == 1
        assert Users.query.filter_by(name="private-original-user").first() is None
        file = TrainingAttachment.query.one(); aid, location = file.id, file.location
    client = login_as_user(app, name="alice"); path = endpoint("bootcamp-2025-3") + f"/files/{aid}"
    assert app.test_client().get(path).status_code == 302
    response = client.get(path)
    assert response.data == b"a fictional exercise artifact" and "no-store" in response.headers["Cache-Control"]
    assert client.get("/files/" + location).status_code == 404
    assert client.get(endpoint("bootcamp-2025-57") + f"/files/{aid}").status_code == 404
    assert client.post(endpoint("bootcamp-2025-3") + "/submit", json={"flag":"secret-two"}).json["status"] == "correct"


def test_bad_export_is_rejected_before_mutation_and_nested_solutions_are_removed(app, tmp_path):
    from CTFd.plugins.cyberdune_training.bootcamp import player_attachment
    archive = tmp_path / "bad.zip"; sample_export(archive, malicious=True)
    with app.app_context(), pytest.raises(ValueError): import_bootcamp(archive)
    with app.app_context(): assert TrainingChallenge.query.count() == 23
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        for name in ["src/challenge.c", "solve.py", "WRITEUP.md", "flag.txt", "README.md"]: z.writestr(name, "content")
    with zipfile.ZipFile(io.BytesIO(player_attachment("exercise.zip", data.getvalue()))) as z: assert z.namelist() == ["src/challenge.c"]
