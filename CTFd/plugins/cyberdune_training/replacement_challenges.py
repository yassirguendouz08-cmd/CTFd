"""Downloadable replacements for the retired built-in browser labs."""
import base64
import codecs
import gzip
import io
import json
import struct
import tarfile
import zipfile


LEGACY_BROWSER_LABS = (
    "header-lab", "rot13-lab", "logs-lab", "archive-lab", "bytecode-lab",
    "stack-lab", "terminal-lab", "reassembly-lab", "pattern-lab",
)

CHALLENGES = (
    dict(slug="response-header", name="Response Header Trace", category="Web", difficulty="Easy", value=50, minutes=10,
         description="Correlate the supplied request and response records by trace ID, select the successful archive export, and decode its response header value.",
         hint="Read the response headers separately from the body, then compare trace IDs and status codes."),
    dict(slug="rot13-recovery", name="Rotated Dispatch", category="Cryptography", difficulty="Easy", value=50, minutes=10,
         description="A short dispatch was encoded with a fixed alphabet rotation. Decode the attached text to recover your flag.",
         hint="The transformation is reversible by applying the same rotation again."),
    dict(slug="event-correlation", name="Event Correlation", category="Forensics", difficulty="Medium", value=200, minutes=35,
         description="Correlate a synthetic event log by request identifier and completion status. Follow the successful export to its evidence record.",
         hint="A nearby timestamp is not enough; match the request_id across the event sequence."),
    dict(slug="archive-route", name="The Archived Route", category="OSINT", difficulty="Hard", value=400, minutes=75,
         description="A fictional organization mirrored several project archives. Use its crawl policy and project index to identify the correct archived record, then recover the training flag. Every person and organization in the files is fictional.",
         hint="Start from the index, follow the matching project's archived path, and reject records whose project identifiers disagree."),
    dict(slug="bytecode-trace", name="Bytecode Trace", category="Reverse Engineering", difficulty="Medium", value=200, minutes=35,
         description="Reverse a tiny instruction trace from the supplied program listing. Reconstruct the output after each LOAD and XOR operation.",
         hint="Each output byte is the loaded value XORed with the immediate operand."),
    dict(slug="stack-snapshot", name="Stack Snapshot", category="Pwn", difficulty="Hard", value=400, minutes=60,
         description="Inspect a synthetic stack snapshot. Decode the saved control-flow record and recover the flag stored in the captured payload. This is a static file exercise; it does not execute native code.",
         hint="The snapshot documents little-endian fields. Decode the payload only after locating its length and offset."),
    dict(slug="hidden-backup", name="Hidden Backup", category="Linux", difficulty="Easy", value=50, minutes=15,
         description="Inspect the supplied backup archive, including hidden paths. Use its manifest to select the current receipt and decode its contents.",
         hint="List the archive contents before extracting it; compare the snapshot labels in the manifest."),
    dict(slug="fragment-courier", name="Fragment Courier", category="Networking", difficulty="Medium", value=200, minutes=35,
         description="Reassemble the out-of-order application fragments in the capture manifest, then decode the recovered message.",
         hint="Sort by the sequence field before joining the fragment data."),
    dict(slug="signal-filter", name="Signal Filter", category="Misc", difficulty="Medium", value=200, minutes=30,
         description="Filter a noisy synthetic record set by the exact label and valid status to recover the training flag.",
         hint="Several records use the right label but are expired. Check both fields."),
    dict(slug="xor-postcard", name="XOR Postcard", category="Cryptography", difficulty="Medium", value=200, minutes=35,
         description="Recover a message encrypted with a short repeating XOR key. The supplied format notes include a known plaintext prefix.",
         hint="XOR the known prefix with the first ciphertext bytes to recover the repeating key."),
    dict(slug="proxy-chain", name="Proxy Chain", category="Web", difficulty="Hard", value=400, minutes=75,
         description="Analyze a fictional reverse-proxy capture and configuration bundle. Reconstruct the normalized route selected by each proxy before identifying the response that contains the flag.",
         hint="Compare the raw path, decoded path, and normalized path at every hop; the final backend sees only the normalized value."),
    dict(slug="field-notes", name="Field Notes", category="OSINT", difficulty="Medium", value=200, minutes=30,
         description="Investigate a fictional archive using the case code and project index. Correlate the matching project with its archived public post, then decode the note. All people, projects, and records are synthetic; no external accounts or websites are involved.",
         hint="Match the exact case code first, then verify both the project and handle before decoding the archived note."),
    dict(slug="client-side-record-gate", name="Client-Side Record Gate", category="Web", difficulty="Medium", value=200, minutes=30,
         description="Audit a fictional offline records viewer. Use the support ticket to identify the requested record, inspect how the browser selects records, and retrieve the matching entry. The files run locally and never contact a server.",
         hint="The page reads a record identifier from the URL. Follow that identifier into the local record catalog."),
    dict(slug="shell-history-recovery", name="Shell History Recovery", category="Linux", difficulty="Medium", value=200, minutes=30,
         description="Review a synthetic home-directory backup. Follow the analyst's shell history to the hidden transfer file, decode it, and read the recovered receipt for your flag.",
         hint="List hidden archive paths, then trace the base64 command recorded in .bash_history."),
    dict(slug="udp-fragment-capture", name="UDP Fragment Capture", category="Networking", difficulty="Medium", value=200, minutes=35,
         description="Analyze a synthetic Ethernet capture. Isolate the UDP stream sent to the training collector, order its numbered fragments, join their hexadecimal data, and decode the result.",
         hint="Filter on UDP destination port 31337. Ignore diagnostic packets without a sequence number."),
)


def rows():
    for item in CHALLENGES:
        yield dict(item, kind="challenge", recipe=item["slug"], active=True, source="CyberDune Academy")


def _zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def artifact(recipe, flag):
    if recipe == "response-header":
        encoded = base64.b64encode(flag.encode()).decode()
        requests = [
            {"trace":"tr-18","method":"GET","path":"/status"},
            {"trace":"tr-42","method":"GET","path":"/archive/export"},
            {"trace":"tr-43","method":"GET","path":"/archive/export"},
        ]
        responses = [
            {"trace":"tr-18","status":200,"headers":{"X-Archive-Note":"bm90LXRoZS1mbGFn"}},
            {"trace":"tr-42","status":503,"headers":{"X-Archive-Note":"c2VydmljZS11bmF2YWlsYWJsZQ=="}},
            {"trace":"tr-43","status":200,"headers":{"X-Archive-Note":encoded}},
        ]
        return "response-trace.zip", _zip({
            "requests.jsonl": ("\n".join(json.dumps(row) for row in requests) + "\n").encode(),
            "responses.jsonl": ("\n".join(json.dumps(row) for row in responses) + "\n").encode(),
        })
    if recipe == "rot13-recovery":
        return "dispatch.txt", (codecs.encode(flag, "rot_13") + "\n").encode()
    if recipe == "event-correlation":
        rows = [
            {"time": "09:00", "request_id": "R17", "event": "export.started"},
            {"time": "09:01", "request_id": "R12", "event": "export.failed"},
            {"time": "09:02", "request_id": "R17", "event": "export.completed"},
            {"time": "09:03", "request_id": "R17", "event": "evidence.saved", "value": flag},
            {"time": "09:04", "request_id": "R12", "event": "evidence.saved", "value": "not-a-flag"},
        ]
        return "event-log.jsonl.gz", gzip.compress("\n".join(json.dumps(row) for row in rows).encode(), mtime=0)
    if recipe == "archive-route":
        files = {
            "START-HERE.txt": b"Find the archive path allowed by the fictional organization index. Match project IDs before reading a record.\n",
            "robots.txt": b"User-agent: *\nDisallow: /mirror/decommissioned/\nDisallow: /mirror/project-d17/\n",
            "index.json": json.dumps({"archives": [
                {"id": "ATLAS-04", "path": "/mirror/project-a04/record.json"},
                {"id": "DESERT-17", "path": "/mirror/project-d17/record.json"},
                {"id": "DUNE-71", "path": "/mirror/project-x71/record.json"},
            ]}).encode(),
            "mirror/project-a04/record.json": json.dumps({"project": "ATLAS-04", "status": "superseded", "note": "c2FtcGxl"}).encode(),
            "mirror/project-d17/record.json": json.dumps({"project": "DESERT-17", "status": "archived", "note": base64.b64encode(flag.encode()).decode()}).encode(),
            "mirror/project-x71/record.json": json.dumps({"project": "DUNE-71", "status": "current", "note": "bm90LXRoZS1mbGFn"}).encode(),
        }
        return "archive-index.zip", _zip(files)
    if recipe == "bytecode-trace":
        lines = ["# Program: LOAD immediate; XOR immediate; OUT", "# Recover bytes in sequence and concatenate them."]
        lines.extend(f"LOAD {byte ^ 42}\nXOR 42\nOUT" for byte in flag.encode())
        return "program.trace", ("\n".join(lines) + "\n").encode()
    if recipe == "stack-snapshot":
        payload = base64.b64encode(flag.encode())
        snapshot = b"SNP1" + len(payload).to_bytes(2, "little") + b"\x00" * 14 + b"EBP!" + bytes.fromhex("e2 91 04 08") + payload
        return "stack.snapshot", snapshot
    if recipe == "hidden-backup":
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            files = {
                "backup/README.txt": b"Use the manifest to select the current snapshot receipt.\n",
                "backup/manifest.json": b'{"current":"snap-12","receipt":".cache/snap-12/receipt.b64"}\n',
                "backup/.cache/snap-11/receipt.b64": base64.b64encode(b"superseded record"),
                "backup/.cache/snap-12/receipt.b64": base64.b64encode(flag.encode()),
            }
            for name, content in files.items():
                info = tarfile.TarInfo(name); info.size = len(content); info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
        return "nightly-backup.tar.gz", output.getvalue()
    if recipe == "fragment-courier":
        encoded = base64.b64encode(flag.encode()).decode()
        size = (len(encoded) + 3) // 4
        chunks = [{"sequence": i + 1, "data": encoded[i * size:(i + 1) * size]} for i in range(4)]
        return "fragments.zip", _zip({"README.txt": b"Sort fragments by sequence, concatenate data, then Base64-decode.\n", "fragments.json": json.dumps(list(reversed(chunks))).encode()})
    if recipe == "signal-filter":
        rows = [
            {"label": "backup.key", "status": "valid", "value": "decoy"},
            {"label": "training.key", "status": "expired", "value": "expired"},
            {"label": "training.key", "status": "valid", "value": flag},
        ]
        return "records.jsonl", ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
    if recipe == "xor-postcard":
        key = b"DUNE"
        ciphertext = bytes(value ^ key[i % len(key)] for i, value in enumerate(flag.encode()))
        return "postcard.json", json.dumps({"known_prefix": "CYBERDUNE{", "ciphertext_hex": ciphertext.hex(), "key_length": len(key)}).encode()
    if recipe == "proxy-chain":
        files = {
            "README.txt": b"Use the config to normalize each request path at both proxy hops. The protected response is in responses.jsonl.\n",
            "proxy.json": json.dumps({"edge_decode": 1, "backend_collapse_slashes": True, "protected_route": "/internal/export"}).encode(),
            "requests.jsonl": ("\n".join(json.dumps({"id": i, "raw_path": path}) for i, path in enumerate(["/public", "/internal/export", "/internal/%65xport", "/internal//export"])) + "\n").encode(),
            "responses.jsonl": ("\n".join(json.dumps({"id": i, "status": 200 if i == 2 else 404, "body": flag if i == 2 else "not found"}) for i in range(4)) + "\n").encode(),
        }
        return "proxy-evidence.zip", _zip(files)
    if recipe == "field-notes":
        rows = [
            "case_code,project,handle,post_type,archived,note_b64",
            "CD-410,ATLAS-04,amber_owl,release,true,bm90LXRoZS1mbGFn",
            "CD-417,LARKSPUR-17,salt_orbit,release,true," + base64.b64encode(flag.encode()).decode(),
            "CD-417,LARKSPUR-17,salt_orbit,draft,false,bm90LXRoZS1mbGFn",
            "CD-417,DECOY-71,amber_owl,release,true,bm90LXRoZS1mbGFn",
        ]
        files = {
            "START-HERE.txt": b"Case CD-417 is linked to a project in the index. Verify the same project and handle in the archived posts; only an archived release is relevant. Decode its note_b64 field.\n",
            "project-index.csv": b"case_code,project,handle\nCD-410,ATLAS-04,amber_owl\nCD-417,LARKSPUR-17,salt_orbit\nCD-417,DECOY-71,amber_owl\n",
            "archived-posts.csv": ("\n".join(rows) + "\n").encode(),
        }
        return "field-notes.zip", _zip(files)
    if recipe == "client-side-record-gate":
        records = {
            "R-12": {"owner": "Public desk", "body": "Public hours: 09:00–17:00."},
            "R-17": {"owner": "Archive team", "body": flag},
            "R-71": {"owner": "Status page", "body": "No incident recorded."},
        }
        files = {
            "README.txt": b"Open index.html locally. The support ticket names the record to review. Inspect records.js and app.js to understand the local viewer.\n",
            "ticket.txt": b"Ticket CD-228: retrieve record R-17 from the fictional archive viewer.\n",
            "index.html": b'<!doctype html><meta charset="utf-8"><title>Offline records</title><h1>Archive viewer</h1><pre id="record">Choose a record with ?record=ID</pre><script src="records.js"></script><script src="app.js"></script>\n',
            "records.js": ("window.RECORDS = " + json.dumps(records) + ";\n").encode(),
            "app.js": b'const id = new URLSearchParams(location.search).get("record"); document.querySelector("#record").textContent = window.RECORDS[id]?.body || "Record not found";\n',
        }
        return "client-side-records.zip", _zip(files)
    if recipe == "shell-history-recovery":
        encoded = base64.b64encode(("receipt=CD-RECOVERY\n" + flag + "\n").encode())
        files = {
            "case/README.txt": b"Synthetic analyst home-directory backup. Review hidden paths and follow the commands in .bash_history.\n",
            "case/home/analyst/.bash_history": b"ls -la\nbase64 -d ~/.cache/export.b64 > /tmp/export.txt\ngrep RECOVERY /tmp/export.txt\n",
            "case/home/analyst/.cache/export.b64": encoded,
            "case/home/analyst/notes.txt": b"Old transfer: this sample is not the current receipt.\n",
        }
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for name, content in files.items():
                info = tarfile.TarInfo(name); info.size = len(content); info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
        return "shell-history-case.tar.gz", output.getvalue()
    if recipe == "udp-fragment-capture":
        def checksum(data):
            if len(data) % 2:
                data += b"\x00"
            total = sum(struct.unpack("!" + "H" * (len(data) // 2), data))
            total = (total & 0xffff) + (total >> 16)
            total = (total & 0xffff) + (total >> 16)
            return (~total) & 0xffff

        def packet(payload, source_port, dest_port, ident):
            udp = struct.pack("!HHHH", source_port, dest_port, 8 + len(payload), 0) + payload
            src = bytes((192, 0, 2, 10)); dst = bytes((198, 51, 100, 20))
            ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), ident, 0, 64, 17, 0, src, dst)
            ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
            return bytes.fromhex("0200000000020200000000010800") + ip + udp

        encoded = flag.encode().hex()
        width = (len(encoded) + 3) // 4
        chunks = [encoded[i * width:(i + 1) * width] for i in range(4)]
        packets = [
            (b"diagnostic keepalive", 40000, 31337),
            (f"seq=3/4;hex={chunks[2]}".encode(), 40002, 31337),
            (f"seq=1/4;hex={chunks[0]}".encode(), 40001, 31337),
            (b"seq=1/1;hex=6465636f79", 40003, 31338),
            (f"seq=4/4;hex={chunks[3]}".encode(), 40004, 31337),
            (f"seq=2/4;hex={chunks[1]}".encode(), 40005, 31337),
        ]
        pcap = bytearray(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for index, (payload, source_port, dest_port) in enumerate(packets):
            frame = packet(payload, source_port, dest_port, index + 1)
            pcap.extend(struct.pack("<IIII", 1_800_000_000 + index, 0, len(frame), len(frame)))
            pcap.extend(frame)
        return "dns-fragments.pcap", bytes(pcap)
    raise KeyError(recipe)
