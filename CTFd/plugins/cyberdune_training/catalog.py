"""Original starter exercises. Artifacts contain per-user flags, never real data."""
import base64
import hashlib
import io
import json
import zlib
import struct
import tarfile
import zipfile

CATEGORIES = ("Web", "Cryptography", "Forensics", "OSINT", "Reverse Engineering", "Pwn", "Linux", "Networking", "Misc")

# slug, title, category, kind, instructions, free hint
STARTERS = [
    ("source-review", "Behind the page", "Web", "challenge", "Download the fictional portal response, locate its audit note, and decode the short letter-shifted value to recover your flag.", "Inspect the HTML comment. Its letters use a reversible alphabet rotation."),
    ("base64-trail", "The encoded dispatch", "Cryptography", "challenge", "Trace the accepted delivery to its envelope. Decode the envelope, match its key ID in the keyring, reverse the repeating XOR mask, and verify the CRC before submitting the recovered flag.", ""),
    ("image-metadata", "More than pixels", "Forensics", "challenge", "Inspect the image metadata to find its acquisition ID. Correlate that ID with the verified evidence record, use its key ID to reverse the byte mask, and validate the recovered record checksum.", ""),
    ("public-trail", "The club archive", "OSINT", "challenge", "Investigate the fictional public archive in the ZIP. Cross-reference the briefing's project code with the correct profile, decode its envelope, then use the matching archive key and checksum to recover the flag. No real people need to be contacted.", ""),
    ("xor-blueprint", "A small obfuscator", "Reverse Engineering", "challenge", "Download the Python verifier. Understand its byte transformation and reverse it to recover the required input. Run downloaded code only in your own practice workspace.", "Each byte was XORed with one fixed byte. XOR with the same key reverses the operation."),
    ("endian-note", "The memory envelope", "Pwn", "challenge", "Inspect a synthetic memory dump. Decode its little-endian length field, then use the key byte in the header to reverse the payload mask.", "Read the binary header field by field; the payload bytes are transformed."),
    ("hidden-files", "Dotfile delivery", "Linux", "challenge", "Inspect the provided tar archive in a practice directory. Reconcile its snapshot manifest, locate the current hidden receipt, decode its layers, and use the referenced key to recover the flag. Do not extract untrusted archives into important folders.", ""),
    ("packet-courier", "One packet, one clue", "Networking", "challenge", "Analyze the synthetic capture in Wireshark. Isolate the complete collector session, reassemble its numbered fragments, reverse the session key's repeating XOR mask, and validate the CRC. Addresses use documentation-only ranges.", ""),
    ("archive-layers", "Another layer", "Misc", "challenge", "Work through the ZIP archive's encoding layers, identify the key material in the evidence notes, reverse the byte mask, and verify the final checksum to recover your flag.", ""),
]


def starter_rows():
    for slug, name, category, kind, description, hint in STARTERS:
        yield dict(slug=slug, name=name, category=category, kind=kind, recipe=slug,
                   difficulty="Medium" if kind == "lab" or slug in {"base64-trail", "image-metadata", "public-trail", "hidden-files", "packet-courier", "archive-layers"} else "Easy",
                   description=description, hint=hint,
                   value=100 if kind == "lab" else 200 if slug in {"base64-trail", "image-metadata", "public-trail", "hidden-files", "packet-courier", "archive-layers"} else 50,
                   minutes=20 if kind == "lab" else 30 if slug in {"base64-trail", "image-metadata", "public-trail", "hidden-files", "packet-courier", "archive-layers"} else 10, active=True)


def zip_bytes(files):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return data.getvalue()


def _xor_repeating(data, key):
    return bytes(value ^ key[index % len(key)] for index, value in enumerate(data))


def _sealed_record(record_id, key_id, plaintext, key):
    ciphertext = _xor_repeating(plaintext, key)
    return {
        "record_id": record_id,
        "key_id": key_id,
        "ciphertext_hex": ciphertext.hex(),
        "crc32": f"{zlib.crc32(plaintext) & 0xffffffff:08x}",
    }


def _yassir_gift_artifact(flag):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os

    case_id, operator_id, phrase = "GIFT-17", "OP-44", "silver dune lantern"
    salt, nonce = os.urandom(16), os.urandom(12)
    iterations = 120_000
    key = hashlib.pbkdf2_hmac("sha256", phrase.encode(), salt, iterations, dklen=32)
    ciphertext = AESGCM(key).encrypt(nonce, flag.encode(), case_id.encode())
    envelope = {
        "case_id": case_id,
        "salt_hex": salt.hex(),
        "nonce_hex": nonce.hex(),
        "iterations": iterations,
        "ciphertext_and_tag_b64": base64.b64encode(ciphertext).decode(),
    }
    audit = [
        {"case_id": "GIFT-11", "operator_id": operator_id, "status": "approved", "phrase": "retired winter signal"},
        {"case_id": case_id, "operator_id": "OP-71", "status": "approved", "phrase": "paper lantern silver"},
        {"case_id": case_id, "operator_id": operator_id, "status": "revoked", "phrase": "copper moon signal"},
        {"case_id": case_id, "operator_id": operator_id, "status": "approved", "phrase": phrase},
    ]
    return "yassir-gift-case.zip", zip_bytes({
        "ticket.txt": b"Recovery request: case GIFT-17, operator OP-44. Use only the approved audit record for this exact pair.\n",
        "audit.jsonl": ("\n".join(json.dumps(row) for row in audit) + "\n").encode(),
        "envelope.b64": base64.b64encode(json.dumps(envelope, separators=(",", ":")).encode()) + b"\n",
        "format.txt": b"envelope.b64 is Base64-encoded JSON. Derive a 32-byte key with PBKDF2-HMAC-SHA256 using the selected audit phrase, salt_hex and iterations. Decrypt ciphertext_and_tag_b64 with AES-256-GCM using nonce_hex and case_id UTF-8 bytes as associated data. Authentication failure means the record or parameters are wrong.\n",
    })


def artifact(recipe, flag):
    from .authored_challenges import CHALLENGES as AUTHORED, artifact as authored_artifact
    if recipe in {row["slug"] for row in AUTHORED}:
        return authored_artifact(recipe, flag)
    from .replacement_challenges import CHALLENGES as REPLACEMENTS, artifact as replacement_artifact
    if recipe in {row["slug"] for row in REPLACEMENTS}:
        return replacement_artifact(recipe, flag)
    from .advanced import ADVANCED, artifact as advanced_artifact
    if recipe in {row["slug"] for row in ADVANCED}:
        return advanced_artifact(recipe, flag)
    if recipe == "yassir-gift":
        return _yassir_gift_artifact(flag)
    encoded = base64.b64encode(flag.encode()).decode()
    if recipe == "source-review":
        import codecs
        return "portal.html", ("<!doctype html><title>Training portal</title><h1>Nothing hidden here?</h1>\n<!-- audit-note: " + codecs.encode(flag, "rot_13") + " -->").encode()
    if recipe == "base64-trail":
        keyring = {"K-2": "SAND", "K-8": "TIDE", "K-9": "DUNE"}
        records = [
            _sealed_record("D-101", "K-8", b"maintenance window moved", keyring["K-8"].encode()),
            _sealed_record("D-204", "K-2", flag.encode(), keyring["K-2"].encode()),
            _sealed_record("D-319", "K-9", b"CYBERDUNE{retired_dispatch}", keyring["K-9"].encode()),
        ]
        envelopes = [{"envelope_b64": base64.b64encode(json.dumps(row, separators=(",", ":")).encode()).decode()} for row in records]
        return "dispatch-investigation.zip", zip_bytes({
            "START-HERE.txt": b"Ticket CR-47 concerns delivery D-204 to node-7. Check the delivery log, then inspect the matching envelope. The decoded JSON provides a key ID, hex ciphertext, and CRC32 of the clear bytes.\n",
            "delivery-log.csv": b"delivery_id,recipient,status\nD-101,node-7,retry\nD-204,node-7,accepted\nD-319,node-9,accepted\n",
            "envelopes.jsonl": ("\n".join(json.dumps(row) for row in envelopes) + "\n").encode(),
            "keyring.json": json.dumps(keyring, sort_keys=True).encode(),
        })
    if recipe == "image-metadata":
        from PIL import Image, PngImagePlugin
        data = io.BytesIO(); metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Acquisition-ID", "ACQ-42")
        Image.new("RGB", (240, 120), "#16171b").save(data, format="PNG", pnginfo=metadata)
        keyring = {"K-4": "MINT", "K-7": "SILT", "K-9": "DUNE"}
        records = [
            _sealed_record("EV-11", "K-4", b"unverified copy", keyring["K-4"].encode()) | {"acquisition_id": "ACQ-41", "state": "verified"},
            _sealed_record("EV-42", "K-7", flag.encode(), keyring["K-7"].encode()) | {"acquisition_id": "ACQ-42", "state": "verified"},
            _sealed_record("EV-43", "K-9", b"quarantined record", keyring["K-9"].encode()) | {"acquisition_id": "ACQ-42", "state": "quarantined"},
        ]
        return "evidence-case.zip", zip_bytes({
            "evidence.png": data.getvalue(),
            "chain-of-custody.json": json.dumps(records, sort_keys=True).encode(),
            "keyring.json": json.dumps(keyring, sort_keys=True).encode(),
        })
    if recipe == "public-trail":
        keyring = {"P-4": "COVE", "P-9": "REEF"}
        envelope = _sealed_record("POST-17", "P-4", flag.encode(), keyring["P-4"].encode())
        stale = _sealed_record("POST-04", "P-9", b"superseded archive note", keyring["P-9"].encode())
        return "club-archive.zip", zip_bytes({
            "briefing.txt": "Fictional archive. Follow the DESERT-17 project reference to its archived profile. Decode the archive_note envelope, match the key ID, and check the checksum.\n",
            "profiles/atlas.json": json.dumps({"project": "ATLAS-04", "archive_note": "bm90IHRoZSBmbGFn"}),
            "profiles/dune.json": json.dumps({"project": "DESERT-17", "archive_note": base64.b64encode(json.dumps(envelope, separators=(",", ":")).encode()).decode()}),
            "profiles/dune-old.json": json.dumps({"project": "DESERT-17", "archive_note": base64.b64encode(json.dumps(stale, separators=(",", ":")).encode()).decode()}),
            "keyring.json": json.dumps(keyring, sort_keys=True),
        })
    if recipe == "xor-blueprint":
        payload = [byte ^ 42 for byte in flag.encode()]
        return "verifier.py", ("# Synthetic reverse-engineering exercise.\nexpected = " + repr(payload) + "\nanswer = input('Recovered input: ')\nprint('Correct' if [ord(c) ^ 42 for c in answer] == expected else 'Try again')\n").encode()
    if recipe == "endian-note":
        payload = flag.encode()
        key = 0x6D
        return "memory.bin", b"MEM1" + struct.pack("<H", len(payload)) + bytes((key,)) + bytes(value ^ key for value in payload) + b"\x00" * 32
    if recipe == "hidden-files":
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w:gz") as archive:
            files = {
                "workspace/README.txt": b"Compare the snapshot manifest, inspect the selected hidden receipt, and use the referenced key to restore its checksum-verified contents.\n",
                "workspace/manifest.json": b'{"current_snapshot":"nightly-07","receipt":".config/nightly-07/receipt.b64","key_id":"K-07","encoding":"base64(hex(xor(clear,key)))"}\n',
                "workspace/.config/old/training.txt": b"decoy record\n",
                "workspace/.config/nightly-06/receipt.b64": base64.b64encode(b"expired snapshot\n"),
                "workspace/.config/nightly-07/receipt.b64": base64.b64encode(_xor_repeating(flag.encode(), b"SAND").hex().encode()),
                "workspace/.config/keys.json": b'{"K-07":"SAND"}\n',
                "workspace/.config/nightly-07/receipt.crc32": f"{zlib.crc32(flag.encode()) & 0xffffffff:08x}\n".encode(),
            }
            for name, content in files.items():
                info = tarfile.TarInfo(name); info.size = len(content); info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
        return "workspace.tar.gz", data.getvalue()
    if recipe == "packet-courier":
        from .authored_challenges import _udp_frame
        keyring = {"K-3": "TIDE", "K-7": "SAND"}
        clear = flag.encode(); cipher = _xor_repeating(clear, keyring["K-7"].encode())
        width = (len(cipher) + 2) // 3
        chunks = [cipher[i * width:(i + 1) * width] for i in range(3)]
        checksum = f"{zlib.crc32(clear) & 0xffffffff:08x}"
        packets = []
        for session, seq, kid, crc, chunk in [
            ("S-42", 2, "K-7", checksum, chunks[1]),
            ("S-11", 1, "K-3", "00000000", b"decoy"),
            ("S-42", 1, "K-7", checksum, chunks[0]),
            ("S-42", 3, "K-7", checksum, chunks[2]),
        ]:
            payload = f"sid={session};seq={seq}/3;kid={kid};crc={crc};hex={chunk.hex()}".encode()
            packets.append(_udp_frame(payload, "192.0.2.10", "198.51.100.20", 40000 + seq, 31337, len(packets) + 1))
        pcap = bytearray(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for index, frame in enumerate(packets):
            pcap.extend(struct.pack("<IIII", 1_800_000_000 + index, 0, len(frame), len(frame)))
            pcap.extend(frame)
        return "courier-case.zip", zip_bytes({
            "capture.pcap": bytes(pcap),
            "session-notes.txt": b"The case ticket names session S-42. Data packets use UDP port 31337; payloads include session, sequence/total, key ID, CRC32 and hex ciphertext. Reassemble sequences, apply the repeating XOR key, then verify CRC32.\n",
            "keyring.json": json.dumps(keyring, sort_keys=True).encode(),
        })
    if recipe == "archive-layers":
        key = b"DUNE"
        ciphertext = _xor_repeating(flag.encode(), key)
        nested = base64.b64encode(ciphertext)
        return "layers.zip", zip_bytes({
            "README.txt": b"Decode payload.hex to bytes, Base64-decode the resulting text, then reverse the repeating XOR using the supplied key. Verify the recovered text with the CRC32 in the manifest.\n",
            "payload.hex": nested.hex().encode() + b"\n",
            "key.txt": b"DUNE\n",
            "manifest.json": json.dumps({"payload": "payload.hex", "xor_key": "key.txt", "crc32": f"{zlib.crc32(flag.encode()) & 0xffffffff:08x}"}).encode(),
        })
    raise ValueError("This exercise has no downloadable artifact")
