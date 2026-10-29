"""Downloadable replacements for the retired built-in browser labs."""
import base64
import codecs
import gzip
import io
import json
import tarfile
import zipfile


LEGACY_BROWSER_LABS = (
    "header-lab", "rot13-lab", "logs-lab", "archive-lab", "bytecode-lab",
    "stack-lab", "terminal-lab", "reassembly-lab", "pattern-lab",
)

CHALLENGES = (
    dict(slug="response-header", name="Response Header Trace", category="Web", difficulty="Easy", value=50, minutes=10,
         description="Inspect the supplied HTTP response capture and recover the training flag from the relevant response header.",
         hint="Read the response headers separately from the body."),
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
         description="Inspect the supplied backup archive, including hidden paths, to find the training flag.",
         hint="List the archive contents before extracting it; dot-prefixed paths are easy to miss."),
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
        return "response.txt", ("HTTP/1.1 200 OK\nContent-Type: text/plain\nX-Training-Flag: " + flag + "\n\nRequest completed.\n").encode()
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
            files = {"backup/README.txt": b"Inspect all backup paths, including hidden entries.\n", "backup/.config/training/flag.txt": flag.encode()}
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
    raise KeyError(recipe)
