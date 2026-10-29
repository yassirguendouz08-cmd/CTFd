"""Original, personalized offline exercises with independently testable solutions."""
import gzip
import hashlib
import io
import json
import random
import struct
import zipfile

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ADVANCED = [
    dict(slug="fault-line", name="Fault line", category="Cryptography", minutes=120,
         description="A fictional HSM produced two raw RSA signatures for the same audit digest. One survived a hardware fault. Recover the sealed incident report from the exported evidence. The archive documents the report's key derivation, but contains no private key. All material is generated for your account.",
         hint="A faulty CRT result can agree with the correct signature modulo one prime, but not the other."),
    dict(slug="dune-vm", name="DuneVM: backward execution", category="Reverse Engineering", minutes=120,
         description="An unfamiliar 64-bit virtual machine transformed the bytes of your access token. Reconstruct the interpreter from its instruction specification, reverse the bytecode, and recover the original input. Your bytecode and target are generated for your account.",
         hint="Execution is reversible. Reverse the instruction order as well as each operation; arithmetic wraps modulo 2^64."),
    dict(slug="clock-drift", name="Clock drift: quorum recovery", category="Forensics", minutes=150,
         description="A synthetic incident spans three clocks, a noisy authentication trail and a binary share capture. Identify the authorized recovery session, correlate its acknowledgements within the documented time window, and reconstruct the key needed to decrypt the evidence. Do not trust every share in the capture.",
         hint="Normalize timestamps first. Reconstruct each key byte using polynomial interpolation over the field stated in FORMAT.md."),
]


def advanced_rows():
    for item in ADVANCED:
        yield dict(item, kind="challenge", recipe=item["slug"], difficulty="Hard", value=400, active=True)


def bundle(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return out.getvalue()


def artifact(recipe, flag):
    # Every instance is reproducible except the deliberately fresh RSA key pair.
    seed = hashlib.sha256(("advanced:v1:" + flag).encode()).digest()
    rng = random.Random(int.from_bytes(seed, "big"))
    if recipe == "fault-line":
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_numbers()
        n, e, p, q, d = key.public_numbers.n, key.public_numbers.e, key.p, key.q, key.d
        message = int.from_bytes(hashlib.sha256(b"CyberDune synthetic HSM audit v1").digest(), "big")
        signature = pow(message, d, n)
        sp = (pow(message, d % (p - 1), p) + 1) % p
        sq = pow(message, d % (q - 1), q)
        faulty = (sq + q * ((sp - sq) * pow(q, -1, p) % p)) % n
        instance = seed[:12].hex()
        factor = min(p, q).to_bytes(128, "big")
        aes_key = hashlib.sha256(b"cyberdune-hsm-v1:" + factor + bytes.fromhex(instance)).digest()
        nonce = seed[12:24]
        ciphertext = AESGCM(aes_key).encrypt(nonce, flag.encode(), instance.encode())
        return "fault-line.zip", bundle({
            "audit.json": json.dumps(dict(n=str(n), e=e, digest=str(message), signature=str(signature), faulty_signature=str(faulty), instance=instance, nonce=nonce.hex())),
            "sealed.bin": ciphertext,
            "FORMAT.md": "# Synthetic HSM evidence\nTwo raw RSA signatures cover the same integer digest. One CRT computation was corrupted.\nReport format: AES-256-GCM ciphertext followed by its 16-byte tag.\nKey = SHA256(b'cyberdune-hsm-v1:' + smaller_prime.to_bytes(128, 'big') + bytes.fromhex(instance)).\nNonce is in audit.json; authenticated data is instance encoded as ASCII. No real HSM or third-party target is involved.\n",
        })
    if recipe == "dune-vm":
        mask = (1 << 64) - 1
        data = bytes([len(flag)]) + flag.encode()
        data += bytes((-len(data)) % 8)
        registers = list(struct.unpack("<" + "Q" * (len(data) // 8), data))
        program = bytearray()
        for _ in range(192):
            op = rng.randrange(1, 6); a = rng.randrange(len(registers)); b = rng.randrange(len(registers) - 1)
            if b >= a: b += 1
            operand = rng.getrandbits(64) | 1
            if op == 4: operand = rng.randrange(1, 64)
            program.extend(struct.pack("<BBBQ", op, a, b, operand))
            if op == 1: registers[a] = (registers[a] + operand) & mask
            elif op == 2: registers[a] ^= operand
            elif op == 3: registers[a] = (registers[a] * operand) & mask
            elif op == 4: registers[a] = ((registers[a] << operand) | (registers[a] >> (64 - operand))) & mask
            else: registers[a] ^= registers[b]
        return "dune-vm.zip", bundle({
            "program.bin": program,
            "target.bin": struct.pack("<" + "Q" * len(registers), *registers),
            "ISA.md": "# DuneVM v1\nInput: a one-byte ASCII token length, that many token bytes, then zero padding to an 8-byte boundary. Load little-endian unsigned 64-bit registers in order.\nInstructions are packed <BBBQ (11 bytes): opcode, destination register a, source register b, immediate k.\n1: a += k; 2: a ^= k; 3: a *= k (k is odd); 4: a = rotate_left_64(a,k); 5: a ^= b.\nAll arithmetic wraps at 64 bits; source b is a distinct register. Execute in file order and dump all registers little-endian to produce target.bin. Recover the input token.\n",
        })
    if recipe == "clock-drift":
        key = bytes(rng.randrange(256) for _ in range(32))
        polynomials = [(v, rng.randrange(257), rng.randrange(257)) for v in key]
        session = seed[:8].hex()
        session_id = rng.randrange(10_000, 90_000)
        offsets = {"auth": 37, "edge": -19, "capture": 83}
        auth, edge, frames = [], [], []
        slots = rng.sample(range(240), 5)
        good = sorted(rng.sample(slots, 3))
        for i in range(240):
            uid = session_id if i in slots else rng.randrange(100_000, 999_999)
            x = good.index(i) + 1 if i in good else rng.randrange(4, 256)
            true_time = 1_800_000_000 + i * 7
            values = [(a + b * x + c * x * x) % 257 for a, b, c in polynomials] if i in good else [rng.randrange(257) for _ in key]
            frames.append(struct.pack("<IIB32H", uid, true_time + offsets["capture"], x, *values))
            edge.append(dict(session_id=uid, event="share.ack", t=true_time + offsets["edge"] + (0 if i in good else 12), share_x=x))
            if i in slots:
                auth.append(dict(session_id=uid, label=session, role="recovery" if i in good else "guest", result="allow" if i in good else "deny", t=true_time + offsets["auth"]))
            else:
                auth.append(dict(session_id=uid, label=f"noise-{i}", role=rng.choice(["guest", "recovery"]), result=rng.choice(["allow", "deny"]), t=true_time + offsets["auth"]))
        rng.shuffle(auth); rng.shuffle(edge); rng.shuffle(frames)
        nonce = seed[8:20]
        return "clock-drift.zip", bundle({
            "auth.jsonl.gz": gzip.compress("\n".join(json.dumps(r) for r in auth).encode(), mtime=0),
            "edge.jsonl.gz": gzip.compress("\n".join(json.dumps(r) for r in edge).encode(), mtime=0),
            "shares.bin": b"".join(frames),
            "sealed.bin": AESGCM(key).encrypt(nonce, flag.encode(), session.encode()),
            "incident.json": json.dumps(dict(label=session, nonce=nonce.hex(), clocks=offsets)),
            "FORMAT.md": "# Synthetic recovery capture\nClock offsets are local-minus-reference seconds, listed in incident.json. All records are fictional.\nCorrelate the incident label's allowed recovery authentication events with share.ack records and binary frames by session_id and share_x. Accept only acknowledgements within 2 seconds of the authentication in reference time. Several records reuse session IDs.\nBinary frame: <IIB32H (73 bytes), session_id, local capture timestamp, share_x, 32 field values. Match its reference timestamp to the same authentication within 2 seconds.\nEach secret key byte is the constant coefficient of an independent degree-2 polynomial over GF(257); the 32 values are evaluations at share_x. Three distinct valid shares suffice. Other shares belong to unrelated or denied operations.\nReport: AES-256-GCM with a 16-byte appended tag, nonce from incident.json, AAD = incident label encoded as ASCII.\n",
        })
    raise KeyError(recipe)
