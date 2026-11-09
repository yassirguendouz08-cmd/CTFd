"""Original, offline Academy challenges with per-user artifacts and flags."""
import base64
import hashlib
import io
import json
import random
import struct
import tarfile
import zlib
import zipfile


CHALLENGES = (
    dict(slug="cache-boundary", name="Cache Boundary", category="Web", difficulty="Hard", value=400, minutes=75,
         description="Reconstruct the edge's single percent-decoding and path-normalization steps, then correlate the incident trace with the matching backend response. Decode the selected response body to recover your flag.", hint=""),
    dict(slug="nonce-reuse-audit", name="Nonce Reuse Audit", category="Cryptography", difficulty="Hard", value=400, minutes=75,
         description="An audit capture contains encrypted records from a service that reused a stream-cipher nonce. Identify the related key-and-nonce pair, use its known audit message to recover the other plaintext, and submit the recovered flag.", hint=""),
    dict(slug="frame-reassembly", name="Frame Reassembly", category="Forensics", difficulty="Hard", value=400, minutes=75,
         description="A damaged acquisition contains interleaved framed records. Validate their checksums, select the incident session, restore byte order, and decompress the reconstructed evidence to recover your flag.", hint=""),
    dict(slug="atlas-ledger", name="Atlas Ledger", category="OSINT", difficulty="Hard", value=400, minutes=75,
         description="Correlate a fictional case index with two archived public datasets. Resolve the project and alias consistently, apply the release and time constraints, then reverse the archive's documented byte transform. No real people, accounts, or websites are involved.", hint=""),
    dict(slug="opcode-relay", name="Opcode Relay", category="Reverse Engineering", difficulty="Hard", value=400, minutes=90,
         description="Reverse a compact virtual-machine program from its instruction specification and bytecode. Execute the state transformations in order, then recover the original input from the final register file.", hint=""),
    dict(slug="heap-ledger", name="Heap Ledger", category="Pwn", difficulty="Hard", value=400, minutes=75,
         description="Analyze a static allocator snapshot. Reconstruct the protected tcache link, locate the referenced object in the memory image, and undo its pointer-derived byte mask. The exercise does not execute native code.", hint=""),
    dict(slug="rotation-recovery", name="Rotation Recovery", category="Linux", difficulty="Hard", value=400, minutes=75,
         description="Examine a synthetic Linux home-directory backup and rotated audit logs. Identify the account and session that produced the surviving transfer, follow its recorded shell commands, and decode the recovered receipt.", hint=""),
    dict(slug="dns-exfiltration", name="DNS Exfiltration", category="Networking", difficulty="Hard", value=400, minutes=75,
         description="Investigate a synthetic DNS capture for a fictional exfiltration session. Isolate the correct client and query domain, order the fragments by their labels, and decode the completed payload.", hint=""),
    dict(slug="constraint-mosaic", name="Constraint Mosaic", category="Misc", difficulty="Hard", value=400, minutes=75,
         description="Reconcile two synthetic maintenance ledgers using the acceptance rules and cutoff time. Select the only valid run, restore its ordered blocks, and reverse the run-specific transform to obtain your flag.", hint=""),
    dict(slug="tcache-chain", name="Tcache Chain", category="Pwn", difficulty="Hard", value=450, minutes=90,
         description="Reconstruct two safe-linked allocator chains from a synthetic heap snapshot. Follow the designated bin to its terminal entry, identify the surviving record in that chunk, and reverse its pointer-derived mask. No native code is executed.", hint=""),
    dict(slug="journal-window", name="Journal Window", category="Linux", difficulty="Hard", value=450, minutes=90,
         description="Correlate a synthetic system journal across boots, users, and process IDs to identify the transfer belonging to the surviving SSH session. Recover its hidden receipt using the documented encoding steps.", hint=""),
    dict(slug="sequence-window", name="Sequence Window", category="Networking", difficulty="Hard", value=450, minutes=90,
         description="Analyze a synthetic UDP capture with interleaved sessions, out-of-order fragments, and a damaged duplicate. Validate each decoded record, reconstruct the complete sequence, and recover the message.", hint=""),
    dict(slug="http-page-capture", name="HTTP Page Capture", category="Networking", difficulty="Medium", value=250, minutes=40,
         description="Inspect a synthetic HTTP capture in Wireshark. Find the dashboard page, follow its referenced resource through the TCP stream, and decode the matching response body to recover your flag. The capture is offline and contains no real services.", hint=""),
)


def rows():
    for item in CHALLENGES:
        yield dict(item, kind="challenge", recipe=item["slug"], active=True, source="Original CyberDune challenge")


def _zip(files):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return data.getvalue()


def _udp_frame(payload, source, destination, source_port, destination_port, ident):
    udp = struct.pack("!HHHH", source_port, destination_port, 8 + len(payload), 0) + payload
    src = bytes(map(int, source.split(".")))
    dst = bytes(map(int, destination.split(".")))
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), ident, 0, 64, 17, 0, src, dst)
    words = struct.unpack("!10H", ip)
    checksum = sum(words)
    checksum = (checksum & 0xffff) + (checksum >> 16)
    checksum = (checksum & 0xffff) + (checksum >> 16)
    ip = ip[:10] + struct.pack("!H", (~checksum) & 0xffff) + ip[12:]
    return bytes.fromhex("0200000000020200000000010800") + ip + udp


def _dns_query(name, transaction_id):
    encoded = bytearray()
    for label in name.split("."):
        raw = label.encode("ascii")
        encoded.append(len(raw)); encoded.extend(raw)
    encoded.append(0)
    return struct.pack("!HHHHHH", transaction_id, 0x0100, 1, 0, 0, 0) + encoded + struct.pack("!HH", 16, 1)


def _internet_checksum(data):
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack("!" + "H" * (len(data) // 2), data))
    while total >> 16:
        total = (total & 0xffff) + (total >> 16)
    return (~total) & 0xffff


def _tcp_frame(payload, source, destination, source_port, destination_port, sequence, acknowledgement, flags, ident):
    src = bytes(map(int, source.split(".")))
    dst = bytes(map(int, destination.split(".")))
    tcp = struct.pack("!HHIIHHHH", source_port, destination_port, sequence, acknowledgement,
                      (5 << 12) | flags, 65535, 0, 0) + payload
    pseudo = src + dst + b"\x00\x06" + struct.pack("!H", len(tcp))
    tcp = tcp[:16] + struct.pack("!H", _internet_checksum(pseudo + tcp)) + tcp[18:]
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp), ident, 0, 64, 6, 0, src, dst)
    ip = ip[:10] + struct.pack("!H", _internet_checksum(ip)) + ip[12:]
    return bytes.fromhex("0200000000020200000000010800") + ip + tcp


def _http_pcap(request_flag):
    client, server = "192.0.2.44", "198.51.100.80"
    client_port, server_port = 51514, 80
    client_seq, server_seq = 1000, 9000
    frames = []
    frames.append(_tcp_frame(b"", client, server, client_port, server_port, client_seq, 0, 0x02, 1))
    frames.append(_tcp_frame(b"", server, client, server_port, client_port, server_seq, client_seq + 1, 0x12, 2))
    client_seq += 1; server_seq += 1
    frames.append(_tcp_frame(b"", client, server, client_port, server_port, client_seq, server_seq, 0x10, 3))
    ident = 4

    def emit(direction, payload, split_points=()):
        nonlocal client_seq, server_seq, ident
        if direction == "client":
            source, destination, source_port, destination_port = client, server, client_port, server_port
            sequence, acknowledgement = client_seq, server_seq
        else:
            source, destination, source_port, destination_port = server, client, server_port, client_port
            sequence, acknowledgement = server_seq, client_seq
        cuts = [0] + list(split_points) + [len(payload)]
        pieces = [(cuts[i], payload[cuts[i]:cuts[i + 1]]) for i in range(len(cuts) - 1) if cuts[i] < cuts[i + 1]]
        order = [0, *range(2, len(pieces)), 1] if len(pieces) >= 3 else list(range(len(pieces)))
        for index in order:
            offset, part = pieces[index]
            flags = 0x18 if index == len(pieces) - 1 else 0x10
            frames.append(_tcp_frame(part, source, destination, source_port, destination_port,
                                     sequence + offset, acknowledgement, flags, ident))
            ident += 1
        if direction == "client":
            client_seq += len(payload)
        else:
            server_seq += len(payload)

    def request(path):
        nonlocal ident
        payload = (f"GET {path} HTTP/1.1\r\nHost: dashboard.training.invalid\r\n"
                   "User-Agent: Academy-Archive/1.0\r\nAccept: */*\r\nConnection: keep-alive\r\n\r\n").encode()
        emit("client", payload)

    def response(body, content_type):
        nonlocal ident
        header = (f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n"
                  f"Content-Length: {len(body)}\r\nCache-Control: no-store\r\nConnection: keep-alive\r\n\r\n").encode()
        raw = header + body
        first = min(47, len(raw) - 1); second = min(first + 61, len(raw) - 1)
        emit("server", raw, (first, second))

    request("/status")
    response(b"healthy\n", "text/plain")
    request("/home.html")
    page = (b"<!doctype html><html><head><title>Service dashboard</title></head><body>"
            b"<h1>Archive health</h1><p>Current report: <a href='/assets/health-07.txt'>download report</a></p>"
            b"</body></html>")
    response(page, "text/html; charset=utf-8")
    request("/assets/health-06.txt")
    response(base64.b64encode(b"expired snapshot"), "text/plain")
    request("/assets/health-07.txt")
    response(base64.b64encode(request_flag.encode()), "text/plain")
    pcap = bytearray(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    for index, frame in enumerate(frames):
        pcap.extend(struct.pack("<IIII", 1_800_200_000 + index, 0, len(frame), len(frame)))
        pcap.extend(frame)
    return bytes(pcap)


def artifact(recipe, flag):
    if recipe == "cache-boundary":
        manifest = {
            "decode_percent_once": True,
            "remove_dot_segments_after_decode": True,
            "collapse_duplicate_slashes": True,
            "protected_route": "/internal/export",
        }
        requests = [
            {"id": "q-14", "trace": "edge-72", "path": "/internal/%65xport/../export", "response": "r-9a"},
            {"id": "q-15", "trace": "edge-72", "path": "/internal/%2565xport", "response": "r-10b"},
            {"id": "q-16", "trace": "edge-73", "path": "/internal/export", "response": "r-11c"},
            {"id": "q-17", "trace": "edge-72", "path": "/internal//export/../health", "response": "r-12d"},
        ]
        responses = [
            {"id": "r-9a", "status": 200, "body_b64": base64.b64encode(flag.encode()).decode()},
            {"id": "r-10b", "status": 404, "body_b64": base64.b64encode(b"not found").decode()},
            {"id": "r-11c", "status": 200, "body_b64": base64.b64encode(b"stale cache object").decode()},
            {"id": "r-12d", "status": 403, "body_b64": base64.b64encode(b"denied").decode()},
        ]
        return "cache-boundary.zip", _zip({
            "incident.txt": b"Incident edge-72 attempted the internal export endpoint. Match its request to the protected route, then use the referenced response body.\n",
            "edge-rules.json": json.dumps(manifest).encode(),
            "requests.jsonl": ("\n".join(json.dumps(x) for x in requests) + "\n").encode(),
            "responses.jsonl": ("\n".join(json.dumps(x) for x in responses) + "\n").encode(),
        })

    if recipe == "nonce-reuse-audit":
        xor = lambda a, b: bytes(x ^ y for x, y in zip(a, b))
        known = b"archive=R-417;state=approved;owner=internal;issuer=simulation;nonce=7c1;format=stream-record-v1"
        plaintext = known + b";status=complete"
        target = flag.encode()
        key_stream = hashlib.sha256(b"training-stream-A").digest()
        nonce_stream = hashlib.sha256(b"nonce:7c1").digest()
        stream = hashlib.shake_256(key_stream + nonce_stream).digest(max(len(plaintext), len(target)))
        records = [
            {"record": "A-41", "key_id": "K-4", "nonce": "7c1", "known_plaintext": known.decode(), "ciphertext": xor(plaintext, stream[:len(plaintext)]).hex()},
            {"record": "A-42", "key_id": "K-4", "nonce": "7c1", "ciphertext": xor(target, stream[:len(target)]).hex()},
            {"record": "B-11", "key_id": "K-8", "nonce": "1ab", "ciphertext": hashlib.sha256(b"decoy-1").hexdigest()},
            {"record": "B-12", "key_id": "K-8", "nonce": "1ab", "known_plaintext": "status=archived", "ciphertext": hashlib.sha256(b"decoy-2").hexdigest()},
            {"record": "C-09", "key_id": "K-4", "nonce": "8dd", "ciphertext": hashlib.sha256(b"decoy-3").hexdigest()},
        ]
        # Replace the second ciphertext with one made from the same stream.
        records[1]["ciphertext"] = xor(target, stream[:len(target)]).hex()
        return "nonce-reuse.jsonl", ("# Synthetic stream-cipher audit; ciphertext bytes are hex.\n" + "\n".join(json.dumps(x) for x in records) + "\n").encode()

    if recipe == "frame-reassembly":
        session = b"IR-739"
        packed = zlib.compress(flag.encode(), level=9)
        width = (len(packed) + 3) // 4
        chunks = [packed[i * width:(i + 1) * width] for i in range(4)]
        records = []
        for sequence, chunk in enumerate(chunks, 1):
            header = b"CF" + session + bytes((sequence, 4)) + struct.pack("<H", len(chunk))
            records.append(header + struct.pack("<I", zlib.crc32(chunk)) + chunk)
        noise = b"CFXX-000" + bytes((2, 4)) + struct.pack("<H", 5) + struct.pack("<I", 0) + b"noise"
        records.extend((noise, records[1][:-1] + bytes((records[1][-1] ^ 1,))))
        return "frame-acquisition.bin", b"CDFA1\x00" + b"".join(struct.pack("<H", len(x)) + x for x in (records[3], records[0], records[5], records[2], records[4], records[1]))

    if recipe == "atlas-ledger":
        shift = len("WINDMILL")
        encoded = bytes(value ^ shift for value in flag.encode()).hex()
        files = {
            "case.txt": b"Case CD-731 concerns the WINDMILL initiative. Use only records posted before 2026-09-01; the active completed release must agree across the project and archive ledgers. Each byte in body_hex is XORed with the number of letters in the verified project title.\n",
            "projects.csv": b"case,project,alias,status\nCD-731,WINDMILL,quiet_compass,active\nCD-731,EMBER-04,quiet_compass,retired\nCD-730,WINDMILL,night_index,active\n",
            "archive.csv": ("case,project,alias,kind,posted,body_hex\nCD-731,WINDMILL,quiet_compass,release,2026-08-19," + encoded + "\nCD-731,WINDMILL,quiet_compass,draft,2026-08-21," + bytes(x ^ shift for x in b"not the release").hex() + "\nCD-731,EMBER-04,quiet_compass,release,2026-08-12," + bytes(x ^ 8 for x in b"decoy record").hex() + "\nCD-730,WINDMILL,night_index,release,2026-08-10," + bytes(x ^ shift for x in b"other case").hex() + "\n").encode(),
        }
        return "atlas-ledger.zip", _zip(files)

    if recipe == "opcode-relay":
        seed = int.from_bytes(hashlib.sha256(flag.encode()).digest()[:8], "little")
        rng = random.Random(seed)
        state = bytearray(flag.encode())
        program = bytearray(b"OPR1")
        for _ in range(len(state) * 5):
            op = rng.randrange(1, 5)
            a = rng.randrange(len(state))
            if op == 1:
                key = rng.randrange(256); program.extend((op, a, key)); state[a] ^= key
            elif op == 2:
                key = rng.randrange(1, 256); program.extend((op, a, key)); state[a] = (state[a] + key) & 255
            elif op == 3:
                shift = rng.randrange(1, 8); program.extend((op, a, shift)); state[a] = ((state[a] << shift) | (state[a] >> (8 - shift))) & 255
            else:
                b = rng.randrange(len(state)); program.extend((op, a, b)); state[a], state[b] = state[b], state[a]
        return "opcode-relay.zip", _zip({
            "SPEC.txt": b"OPR1 begins a bytecode stream of 3-byte instructions: 01 index xor-key; 02 index add-key (mod 256); 03 index rotate-left-bits; 04 index swap-index. Registers start as the unknown input bytes. Apply instructions forward to match target.bin; recover the input by reversing instruction order and each operation.\n",
            "program.bin": bytes(program), "target.bin": bytes(state),
        })

    if recipe == "heap-ledger":
        heap_base = 0x555555760000
        chunk = heap_base + 0x2A0
        target = heap_base + 0x410
        encoded_next = target ^ (chunk >> 12)
        memory = bytearray(0x500)
        mask = (target >> 12) & 0xff
        memory[target - heap_base:target - heap_base + len(flag)] = bytes(x ^ mask for x in flag.encode())
        memory[0x180:0x18c] = b"decoy-object"
        info = {"heap_base": hex(heap_base), "chunk_address": hex(chunk), "chunk_size": "0x40", "stored_next": hex(encoded_next), "snapshot_length": len(memory)}
        return "heap-ledger.zip", _zip({
            "allocator.json": json.dumps(info).encode(), "heap.bin": bytes(memory),
            "allocator-notes.txt": b"This build uses safe-linking for singly linked tcache entries: stored_next = next_pointer XOR (chunk_address >> 12). Snapshot bytes are indexed from heap_base. The pointed-to record is byte-masked with the low byte of (next_pointer >> 12).\n",
        })

    if recipe == "rotation-recovery":
        account = "analyst-1042"
        uid = 1042
        key = uid & 0xff
        encoded = bytes(value ^ key for value in flag.encode()).hex().encode()
        files = {
            "etc/passwd.snapshot": b"root:x:0:0:root:/root:/bin/bash\nanalyst:x:1042:1042:analyst:/home/analyst:/bin/bash\nbackup:x:1043:1043:backup:/home/backup:/bin/bash\n",
            "var/log/secure-2026-09-01": b"Sep 01 02:12:08 host sudo: backup : TTY=pts/0 ; USER=root ; COMMAND=/usr/bin/rotate\nSep 01 02:13:41 host sshd[88]: Accepted publickey for analyst from 192.0.2.44\n",
            "var/log/audit-2026-09-01.jsonl": (json.dumps({"time":"02:14:02","uid":1042,"session":"s-81","command":"base64 -d ~/.local/share/.cache/receipt.b64 | xxd -r -p"}) + "\n" + json.dumps({"time":"02:14:03","uid":1043,"session":"s-80","command":"cat /tmp/old-copy"}) + "\n").encode(),
            "home/analyst/.bash_history": b"# 2026-09-01 02:14:02\nbase64 -d ~/.local/share/.cache/receipt.b64 | xxd -r -p\n",
            "home/analyst/.local/share/.cache/receipt.b64": base64.b64encode(encoded),
            "home/backup/old-copy": b"not the incident receipt\n",
            "session.txt": f"Surviving transfer belongs to account {account}; the recovered bytes are XOR-masked by the account UID's low byte.\n".encode(),
        }
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for path, content in files.items():
                info = tarfile.TarInfo(path); info.size = len(content); info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
        return "rotation-recovery.tar.gz", output.getvalue()

    if recipe == "dns-exfiltration":
        from hashlib import sha256
        encoded = base64.b32encode(flag.encode()).decode().rstrip("=").lower()
        width = (len(encoded) + 3) // 4
        fragments = [encoded[i * width:(i + 1) * width] for i in range(4)]
        packets = []
        # Several unrelated queries create noise; the case host and collector suffix are in the incident note.
        names = [
            ("203.0.113.19", "x.part01.noise.training.invalid"),
            ("203.0.113.77", f"case9.p03.{fragments[2]}.sink.training.invalid"),
            ("203.0.113.77", f"case9.p01.{fragments[0]}.sink.training.invalid"),
            ("203.0.113.77", "case8.p01.zm9v.sink.training.invalid"),
            ("203.0.113.77", f"case9.p04.{fragments[3]}.sink.training.invalid"),
            ("203.0.113.77", f"case9.p02.{fragments[1]}.sink.training.invalid"),
        ]
        for index, (source, name) in enumerate(names, 1):
            dns = _dns_query(name, index)
            packets.append(_udp_frame(dns, source, "198.51.100.53", 53000 + index, 53, index))
        pcap = bytearray(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for index, frame in enumerate(packets):
            pcap.extend(struct.pack("<IIII", 1_800_000_000 + index, 0, len(frame), len(frame)))
            pcap.extend(frame)
        return "dns-exfiltration.pcap", bytes(pcap)

    if recipe == "constraint-mosaic":
        seed = "RUN-739"
        key = sum(ord(c) for c in seed) & 0xff
        data = flag.encode()
        width = (len(data) + 3) // 4
        blocks = [data[i * width:(i + 1) * width] for i in range(4)]
        ledger_a = [
            {"run":"RUN-812","operator":"MIRA","state":"accepted","opened":"2026-09-14T09:00Z","closed":"2026-09-14T09:12Z","checksum":"bad"},
            {"run":seed,"operator":"NOVA","state":"accepted","opened":"2026-09-14T09:20Z","closed":"2026-09-14T09:28Z","checksum":"verified"},
            {"run":"RUN-731","operator":"NOVA","state":"accepted","opened":"2026-09-14T10:20Z","closed":"2026-09-14T10:28Z","checksum":"verified"},
            {"run":"RUN-739","operator":"NOVA","state":"rejected","opened":"2026-09-14T09:20Z","closed":"2026-09-14T09:28Z","checksum":"verified"},
        ]
        ledger_b = []
        for run, seq, block, checked in [(seed, 3, blocks[2], blocks[2]), ("RUN-812", 1, b"noise", b"noise"), (seed, 1, blocks[0], blocks[0]), (seed, 4, blocks[3], blocks[3]), (seed, 2, blocks[1], blocks[1]), (seed, 2, bytes(x ^ 1 for x in blocks[1]), blocks[1])]:
            ledger_b.append({"run":run,"sequence":seq,"payload_hex":bytes(x ^ key for x in block).hex(),"crc32":f"{zlib.crc32(checked):08x}"})
        rules = b"Acceptance rules: the authoritative run must be accepted, have a verified checksum, start and finish before 10:00Z, and be signed by an operator listed as active in operators.json. In ledger B, choose the four sequence numbers for that exact run; the recorded CRC is computed over the decoded block before the run transform is reversed. The transform XORs each payload byte with the sum of the selected run identifier's ASCII bytes modulo 256.\n"
        files = {
            "rules.txt": rules,
            "ledger-a.jsonl": ("\n".join(json.dumps(x) for x in ledger_a) + "\n").encode(),
            "ledger-b.jsonl": ("\n".join(json.dumps(x) for x in ledger_b) + "\n").encode(),
            "operators.json": b'{"NOVA":"active","MIRA":"suspended"}\n',
        }
        return "constraint-mosaic.zip", _zip(files)

    if recipe == "tcache-chain":
        heap_base = 0x555555760000
        chunks = {"A": heap_base + 0x2A0, "B": heap_base + 0x340, "C": heap_base + 0x410,
                  "X": heap_base + 0x520}
        # The selected bin walks A -> C -> B -> NULL; X belongs to another bin.
        nodes = []
        for name, target in (("C", "B"), ("X", None), ("A", "C"), ("B", None)):
            address = chunks[name]
            next_address = chunks[target] if target else 0
            nodes.append({"label": name, "chunk": hex(address), "stored_next": hex(next_address ^ (address >> 12)),
                          "bin": "0x40" if name != "X" else "0x80"})
        heap = bytearray(0x600)
        mask = (chunks["B"] >> 12) & 0xff
        start = chunks["B"] - heap_base + 0x10
        heap[start:start + len(flag)] = bytes(byte ^ mask for byte in flag.encode())
        # Decoy bytes occupy a plausible user-data location in the other bin.
        heap[chunks["X"] - heap_base + 0x10:chunks["X"] - heap_base + 0x1C] = b"decoy-record"
        files = {
            "allocator.json": json.dumps({"heap_base": hex(heap_base), "bin_heads": {"0x40": hex(chunks["A"]), "0x80": hex(chunks["X"])}, "nodes": nodes}).encode(),
            "heap.bin": bytes(heap),
            "layout.txt": b"Safe-linking stores next XOR (chunk_address >> 12); a terminal NULL is encoded by XORing zero with that same value. Records begin 0x10 bytes after the chunk address. The surviving record is masked bytewise with the low byte of (its chunk address >> 12). The bin field identifies which chain a node belongs to.\n",
        }
        return "tcache-chain.zip", _zip(files)

    if recipe == "journal-window":
        uid, pid, boot, session = 1027, 7312, "boot-31", "ssh-884"
        key, shift = (uid ^ pid) & 0xff, uid & 7
        def rol(value, amount):
            return ((value << amount) | (value >> (8 - amount))) & 0xff
        encoded = bytes(rol(byte ^ key, shift) for byte in flag.encode()).hex()
        records = [
            {"_BOOT_ID":boot,"_UID":uid,"_PID":pid,"_COMM":"sshd","_AUDIT_SESSION":session,"MESSAGE":"Accepted publickey for operator"},
            {"_BOOT_ID":"boot-22","_UID":uid,"_PID":pid,"_COMM":"sshd","_AUDIT_SESSION":"ssh-882","MESSAGE":"Accepted publickey for operator"},
            {"_BOOT_ID":boot,"_UID":0,"_PID":7312,"_COMM":"sudo","_AUDIT_SESSION":session,"MESSAGE":"rotated logs"},
            {"_BOOT_ID":boot,"_UID":uid,"_PID":pid,"_COMM":"bash","_AUDIT_SESSION":session,"MESSAGE":"cat ~/.local/share/.sync/receipt.hex"},
            {"_BOOT_ID":boot,"_UID":uid,"_PID":7313,"_COMM":"bash","_AUDIT_SESSION":"ssh-883","MESSAGE":"cat /tmp/old-receipt"},
            {"_BOOT_ID":boot,"_UID":1028,"_PID":7312,"_COMM":"bash","_AUDIT_SESSION":session,"MESSAGE":"cat /home/backup/receipt.hex"},
        ]
        files = {
            "journal-export.jsonl": ("\n".join(json.dumps(row) for row in records) + "\n").encode(),
            "etc/passwd.snapshot": b"root:x:0:0:root:/root:/bin/bash\noperator:x:1027:1027:Operator:/home/operator:/bin/bash\nbackup:x:1028:1028:Backup:/home/backup:/bin/bash\n",
            "var/lib/systemd/random-seed.meta": b"Current boot identifier: boot-31\n",
            "home/operator/.local/share/.sync/receipt.hex": encoded.encode(),
            "home/backup/receipt.hex": b"4e4f542d5448452d52454345495054",
            "FORMAT.txt": b"Correlate the accepted SSH session with the same boot identifier, UID, PID, and audit session in the journal. For the resulting receipt, each hex-decoded byte was transformed as ROL8(plaintext XOR ((UID XOR PID) mod 256), UID mod 8). Apply the inverse operations in reverse order.\n",
        }
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for path, content in files.items():
                info = tarfile.TarInfo(path); info.size = len(content); info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
        return "journal-window.tar.gz", output.getvalue()

    if recipe == "sequence-window":
        session = b"R7Q2"
        payload = flag.encode()
        width = (len(payload) + 2) // 3
        chunks = [payload[i * width:(i + 1) * width] for i in range(3)]
        def rol(value, amount):
            return ((value << amount) | (value >> (8 - amount))) & 0xff
        def packet(session_id, sequence, chunk, corrupt=False):
            clear = bytes(x ^ (sequence & 0xff) for x in chunk)
            encoded = bytes(rol(x, (sequence % 7) + 1) for x in clear)
            checksum = zlib.crc32(chunk)
            if corrupt:
                checksum ^= 0x01010101
            return b"CDN1" + session_id + bytes((sequence, 3)) + struct.pack("!H", len(chunk)) + struct.pack("!I", checksum) + encoded
        records = [packet(session, 2, chunks[1]), packet(b"X1Z9", 1, b"decoy"), packet(session, 1, chunks[0]),
                   packet(session, 2, bytes(x ^ 0x20 for x in chunks[1]), corrupt=True), packet(session, 3, chunks[2]),
                   packet(b"R7Q3", 1, b"noise")]
        frames = [_udp_frame(item, "192.0.2.61" if item[4:8] == session else "192.0.2.99", "198.51.100.44", 42000 + i, 40444, i)
                  for i, item in enumerate(records, 1)]
        pcap = bytearray(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for index, frame in enumerate(frames):
            pcap.extend(struct.pack("<IIII", 1_800_100_000 + index, 0, len(frame), len(frame)))
            pcap.extend(frame)
        notes = b"UDP destination port 40444 carries records: magic CDN1, 4-byte session, 1-byte sequence, 1-byte total, 2-byte big-endian decoded length, 4-byte big-endian CRC32 of the clear fragment, then encoded data. Clear bytes are encoded as ROL8(byte XOR (sequence mod 256), (sequence mod 7)+1). Reverse that transform, validate length and CRC, and use only a complete session with all sequence numbers.\n"
        return "sequence-window.zip", _zip({"capture.pcap": bytes(pcap), "record-format.txt": notes})

    if recipe == "http-page-capture":
        return "http-page-capture.pcap", _http_pcap(flag)

    raise KeyError(recipe)
