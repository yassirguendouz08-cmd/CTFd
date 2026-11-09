"""Recover advanced flags from player evidence, without reading generator state."""
import gzip
import base64
import hashlib
import io
import json
import math
import re
import struct
import tarfile
import zipfile

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from CTFd.models import Users, db
from CTFd.plugins.cyberdune_training import exercise_flag
from CTFd.plugins.cyberdune_training.bootcamp import import_bootcamp
from CTFd.plugins.cyberdune_training.models import TrainingAnswer, TrainingAttachment, TrainingChallenge, TrainingSolve
from tests.helpers import login_as_user
from tests.test_cyberdune_training import app, endpoint, solution


@pytest.mark.parametrize("slug", ["fault-line", "dune-vm", "clock-drift"])
def test_advanced_artifacts_have_working_independent_solutions(app, slug):
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
    assert recovered == solution(app, slug)
    assert client.post(endpoint(slug) + "/submit", json={"flag": recovered}).json["status"] == "correct"


@pytest.mark.parametrize("slug", ["field-notes", "client-side-record-gate", "shell-history-recovery", "udp-fragment-capture"])
def test_new_category_challenges_recover_and_accept_the_account_flag(app, slug):
    import csv
    import re

    client = login_as_user(app, name="alice")
    response = client.get(endpoint(slug) + "/artifact")
    assert response.status_code == 200
    if slug == "field-notes":
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            rows = csv.DictReader(io.StringIO(archive.read("archived-posts.csv").decode()))
            row = next(item for item in rows if item["case_code"] == "CD-417" and item["project"] == "LARKSPUR-17" and item["handle"] == "salt_orbit" and item["post_type"] == "release" and item["archived"] == "true")
            recovered = base64.b64decode(row["note_b64"]).decode()
    elif slug == "client-side-record-gate":
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            match = re.search(r"Ticket CD-228: retrieve record (R-\d+)", archive.read("ticket.txt").decode())
            records = json.loads(archive.read("records.js").decode().removeprefix("window.RECORDS = ").rstrip(";\n"))
            recovered = records[match.group(1)]["body"]
    elif slug == "shell-history-recovery":
        with tarfile.open(fileobj=io.BytesIO(response.data), mode="r:gz") as archive:
            payload = archive.extractfile("case/home/analyst/.cache/export.b64").read()
            recovered = base64.b64decode(payload).decode().splitlines()[1]
    else:
        data = response.data
        offset = 24  # classic pcap global header
        fragments = {}
        while offset < len(data):
            _, _, captured, _ = struct.unpack_from("<IIII", data, offset)
            frame = data[offset + 16:offset + 16 + captured]
            offset += 16 + captured
            ip_offset = 14
            udp_offset = ip_offset + (frame[ip_offset] & 0x0f) * 4
            _, dest_port, _, _ = struct.unpack_from("!HHHH", frame, udp_offset)
            if dest_port != 31337:
                continue
            payload = frame[udp_offset + 8:].decode()
            match = re.fullmatch(r"seq=(\d+)/(\d+);hex=([0-9a-f]+)", payload)
            if match:
                fragments[int(match.group(1))] = match.group(3)
        recovered = bytes.fromhex("".join(fragments[index] for index in range(1, 5))).decode()

    assert recovered == solution(app, slug)
    result = client.post(endpoint(slug) + "/submit", json={"flag": recovered})
    assert result.status_code == 200 and result.json["status"] == "correct"


def test_replacement_file_challenges_cover_all_categories_levels_and_solve(app):
    client = login_as_user(app, name="alice")
    slugs = ["response-header", "rot13-recovery", "event-correlation", "archive-route", "bytecode-trace",
             "stack-snapshot", "hidden-backup", "fragment-courier", "signal-filter", "xor-postcard", "proxy-chain"]
    with app.app_context():
        items = TrainingChallenge.query.filter(TrainingChallenge.slug.in_(slugs)).all()
        assert len(items) == len(slugs) and all(row.kind == "challenge" and row.active for row in items)
        assert {row.difficulty for row in items} == {"Easy", "Medium", "Hard"}
        assert {row.category for row in items} >= {"Web", "Cryptography", "Forensics", "OSINT", "Reverse Engineering", "Pwn", "Linux", "Networking", "Misc"}
    for slug in slugs:
        response = client.get(endpoint(slug) + "/artifact")
        assert response.status_code == 200 and "no-store" in response.headers["Cache-Control"]
        data = response.data
        flag = solution(app, slug)
        if slug == "response-header":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                requests = [json.loads(line) for line in archive.read("requests.jsonl").splitlines()]
                responses = [json.loads(line) for line in archive.read("responses.jsonl").splitlines()]
                request = next(row for row in requests if row["path"] == "/archive/export" and row["trace"] == "tr-43")
                response = next(row for row in responses if row["trace"] == request["trace"] and row["status"] == 200)
                recovered = base64.b64decode(response["headers"]["X-Archive-Note"]).decode()
        elif slug == "rot13-recovery":
            import codecs
            recovered = codecs.decode(data.decode().strip(), "rot_13")
        elif slug == "event-correlation":
            events = [json.loads(line) for line in gzip.decompress(data).splitlines()]
            successful = {event["request_id"] for event in events if event["event"] == "export.completed"}
            recovered = next(event["value"] for event in events if event["event"] == "evidence.saved" and event["request_id"] in successful)
        elif slug == "archive-route":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                records = json.loads(archive.read("index.json"))["archives"]
                chosen = next(row for row in records if row["id"] == "DESERT-17")
                note = json.loads(archive.read(chosen["path"].lstrip("/")))["note"]
                recovered = base64.b64decode(note).decode()
        elif slug == "bytecode-trace":
            loads = [int(line.split()[1]) for line in data.decode().splitlines() if line.startswith("LOAD ")]
            recovered = bytes(value ^ 42 for value in loads).decode()
        elif slug == "stack-snapshot":
            size = int.from_bytes(data[4:6], "little")
            recovered = base64.b64decode(data[28:28 + size]).decode()
        elif slug == "hidden-backup":
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
                recovered = base64.b64decode(archive.extractfile("backup/.cache/snap-12/receipt.b64").read()).decode()
        elif slug == "fragment-courier":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                fragments = sorted(json.loads(archive.read("fragments.json")), key=lambda row: row["sequence"])
                recovered = base64.b64decode("".join(row["data"] for row in fragments)).decode()
        elif slug == "signal-filter":
            records = [json.loads(line) for line in data.decode().splitlines()]
            recovered = next(row["value"] for row in records if row["label"] == "training.key" and row["status"] == "valid")
        elif slug == "xor-postcard":
            postcard = json.loads(data)
            cipher = bytes.fromhex(postcard["ciphertext_hex"])
            key = b"DUNE"
            recovered = bytes(value ^ key[index % len(key)] for index, value in enumerate(cipher)).decode()
        else:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                responses = [json.loads(line) for line in archive.read("responses.jsonl").splitlines()]
                recovered = next(row["body"] for row in responses if row["status"] == 200 and row["id"] == 2)
        assert recovered == flag
        assert client.post(endpoint(slug) + "/submit", json={"flag": recovered}).json["status"] == "correct"
    other = login_as_user(app, name="bob")
    assert other.post(endpoint(slug) + "/submit", json={"flag": recovered}).json["status"] == "incorrect"


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
        report = import_bootcamp(archive); assert report == dict(imported=1, published=1, pending=0)
        import_bootcamp(archive)
        assert TrainingChallenge.query.count() == 41 and TrainingAttachment.query.count() == 1 and TrainingAnswer.query.count() == 1
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
    with app.app_context(): assert TrainingChallenge.query.count() == 40
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        for name in ["src/challenge.c", "solve.py", "WRITEUP.md", "flag.txt", "README.md"]: z.writestr(name, "content")
    with zipfile.ZipFile(io.BytesIO(player_attachment("exercise.zip", data.getvalue()))) as z: assert z.namelist() == ["src/challenge.c"]


def test_plain_easy_flag_obfuscation_preserves_binary_offsets():
    from CTFd.plugins.cyberdune_training import obfuscate_visible_flags
    sample = b"prefix\x00CYBERDUNE{reasoning_step_42}\xffsuffix"
    changed = obfuscate_visible_flags(sample)
    assert len(changed) == len(sample)
    assert b"CYBERDUNE{" not in changed
    assert changed.startswith(b"prefix\x00") and changed.endswith(b"\xffsuffix")


def test_http_page_capture_can_be_followed_and_decoded():
    import base64
    import struct
    from CTFd.plugins.cyberdune_training.authored_challenges import _http_pcap

    flag = "CYBERDUNE{synthetic_http_capture_test}"
    capture = _http_pcap(flag)
    assert flag.encode() not in capture
    offset, flows = 24, {}
    while offset < len(capture):
        _, _, size, _ = struct.unpack_from("<IIII", capture, offset)
        offset += 16
        frame = capture[offset:offset + size]
        offset += size
        ip = frame[14:]
        ip_header_size = (ip[0] & 0x0f) * 4
        source = ".".join(map(str, ip[12:16]))
        destination = ".".join(map(str, ip[16:20]))
        tcp = ip[ip_header_size:]
        source_port, destination_port, sequence = struct.unpack_from("!HHI", tcp)
        tcp_header_size = (tcp[12] >> 4) * 4
        payload = tcp[tcp_header_size:]
        if payload:
            flows.setdefault((source, source_port, destination, destination_port), []).append((sequence, payload))

    streams = {}
    for direction, segments in flows.items():
        start = min(sequence for sequence, _ in segments)
        stream = bytearray()
        for sequence, payload in sorted(segments):
            position = sequence - start
            if len(stream) < position + len(payload):
                stream.extend(b"\x00" * (position + len(payload) - len(stream)))
            stream[position:position + len(payload)] = payload
        streams[direction] = bytes(stream)

    client_stream = next(data for direction, data in streams.items() if direction[1] != 80)
    server_stream = next(data for direction, data in streams.items() if direction[1] == 80)
    requests = [line.split()[1].decode() for line in client_stream.split(b"\r\n") if line.startswith(b"GET ")]
    assert requests == ["/status", "/home.html", "/assets/health-06.txt", "/assets/health-07.txt"]

    bodies, cursor = [], 0
    while cursor < len(server_stream):
        boundary = server_stream.find(b"\r\n\r\n", cursor)
        assert boundary >= 0
        headers = server_stream[cursor:boundary].split(b"\r\n")
        content_length = int(next(line.split(b":", 1)[1] for line in headers if line.lower().startswith(b"content-length:")))
        body_start = boundary + 4
        bodies.append(server_stream[body_start:body_start + content_length])
        cursor = body_start + content_length
    assert len(bodies) == len(requests)
    assert b"/assets/health-07.txt" in bodies[1]
    assert base64.b64decode(bodies[3]).decode() == flag


def test_yassir_gift_requires_audit_correlation_and_authenticated_decryption():
    import hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from CTFd.plugins.cyberdune_training.catalog import artifact

    flag = "CYBERDUNE{synthetic_gift_crypto_test}"
    name, data = artifact("yassir-gift", flag)
    assert name == "yassir-gift-case.zip" and flag.encode() not in data
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        ticket = archive.read("ticket.txt").decode()
        case_id = re.search(r"case (GIFT-\d+)", ticket).group(1)
        operator_id = re.search(r"operator (OP-\d+)", ticket).group(1)
        records = [json.loads(line) for line in archive.read("audit.jsonl").splitlines()]
        record = next(row for row in records if row["case_id"] == case_id and row["operator_id"] == operator_id and row["status"] == "approved")
        envelope = json.loads(base64.b64decode(archive.read("envelope.b64")))
        key = hashlib.pbkdf2_hmac("sha256", record["phrase"].encode(), bytes.fromhex(envelope["salt_hex"]), envelope["iterations"], dklen=32)
        recovered = AESGCM(key).decrypt(bytes.fromhex(envelope["nonce_hex"]), base64.b64decode(envelope["ciphertext_and_tag_b64"]), case_id.encode()).decode()
    assert recovered == flag
