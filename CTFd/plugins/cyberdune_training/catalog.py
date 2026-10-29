"""Original starter exercises. Artifacts contain per-user flags, never real data."""
import base64
import io
import json
import struct
import tarfile
import zipfile

CATEGORIES = ("Web", "Cryptography", "Forensics", "OSINT", "Reverse Engineering", "Pwn", "Linux", "Networking", "Misc")

# slug, title, category, kind, instructions, free hint
STARTERS = [
    ("source-review", "Behind the page", "Web", "challenge", "Download the page from a fictional training portal. The visible text is only part of the response. Find the flag without attacking this platform.", "Open the downloaded HTML in a text editor and inspect its comments."),
    ("base64-trail", "The encoded dispatch", "Cryptography", "challenge", "An intercepted fictional dispatch uses a common text encoding. Download and decode it to recover your flag.", "The alphabet and trailing equals signs suggest Base64. Encoding is not encryption."),
    ("image-metadata", "More than pixels", "Forensics", "challenge", "The image is generated for this exercise. Inspect its metadata to find what was preserved alongside the visible pixels.", "Try exiftool or inspect the PNG text chunks."),
    ("public-trail", "The club archive", "OSINT", "challenge", "Investigate the fictional public archive in the ZIP. Cross-reference the briefing's project code with the correct profile. Everything needed is in the archive; no real people need to be contacted.", "Match the project identifier across the briefing and profiles, then decode the matching archive note."),
    ("xor-blueprint", "A small obfuscator", "Reverse Engineering", "challenge", "Download the Python verifier. Understand its byte transformation and reverse it to recover the required input. Run downloaded code only in your own practice workspace.", "Each byte was XORed with one fixed byte. XOR with the same key reverses the operation."),
    ("endian-note", "The memory envelope", "Pwn", "challenge", "Inspect a synthetic memory dump. Its first four bytes encode the length of the message in little-endian order. Recover exactly that many bytes after the header.", "Decode the first four bytes as a little-endian unsigned integer, then slice the following message."),
    ("hidden-files", "Dotfile delivery", "Linux", "challenge", "Inspect the provided tar archive in a practice directory. A hidden configuration directory contains your training flag. Do not extract untrusted archives into important folders.", "Files beginning with a dot are hidden by default. Try tar -tf and ls -la."),
    ("packet-courier", "One packet, one clue", "Networking", "challenge", "Open the synthetic packet capture in Wireshark or another offline packet viewer. Recover the application payload from its UDP datagram. Addresses use documentation-only ranges.", "Inspect the UDP payload or use Follow UDP Stream."),
    ("archive-layers", "Another layer", "Misc", "challenge", "Work through a small ZIP archive. Follow the instructions in order and decode the final message to obtain your flag.", "Read README.txt first. The next file contains hexadecimal text, not raw binary."),
]


def starter_rows():
    for slug, name, category, kind, description, hint in STARTERS:
        yield dict(slug=slug, name=name, category=category, kind=kind, recipe=slug,
                   difficulty="Medium" if kind == "lab" else "Easy",
                   description=description, hint=hint, value=100 if kind == "lab" else 50,
                   minutes=20 if kind == "lab" else 10, active=True)


def zip_bytes(files):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return data.getvalue()


def artifact(recipe, flag):
    from .replacement_challenges import CHALLENGES as REPLACEMENTS, artifact as replacement_artifact
    if recipe in {row["slug"] for row in REPLACEMENTS}:
        return replacement_artifact(recipe, flag)
    from .advanced import ADVANCED, artifact as advanced_artifact
    if recipe in {row["slug"] for row in ADVANCED}:
        return advanced_artifact(recipe, flag)
    from .pico import PICO, artifact as pico_artifact
    if recipe in {row["slug"] for row in PICO}:
        return pico_artifact(recipe, flag)
    encoded = base64.b64encode(flag.encode()).decode()
    if recipe == "source-review":
        return "portal.html", ("<!doctype html><title>Training portal</title><h1>Nothing hidden here?</h1>\n<!-- audit-note: " + flag + " -->").encode()
    if recipe == "base64-trail":
        return "dispatch.txt", (encoded + "\n").encode()
    if recipe == "image-metadata":
        from PIL import Image, PngImagePlugin
        data = io.BytesIO(); metadata = PngImagePlugin.PngInfo()
        metadata.add_text("TrainingEvidence", flag)
        Image.new("RGB", (240, 120), "#16171b").save(data, format="PNG", pnginfo=metadata)
        return "evidence.png", data.getvalue()
    if recipe == "public-trail":
        return "club-archive.zip", zip_bytes({
            "briefing.txt": "Fictional CyberDune archive. Find project DESERT-17 and decode its archive_note.\n",
            "profiles/atlas.json": json.dumps({"project": "ATLAS-04", "archive_note": "bm90IHRoZSBmbGFn"}),
            "profiles/dune.json": json.dumps({"project": "DESERT-17", "archive_note": encoded}),
        })
    if recipe == "xor-blueprint":
        payload = [byte ^ 42 for byte in flag.encode()]
        return "verifier.py", ("# Synthetic reverse-engineering exercise.\nexpected = " + repr(payload) + "\nanswer = input('Recovered input: ')\nprint('Correct' if [ord(c) ^ 42 for c in answer] == expected else 'Try again')\n").encode()
    if recipe == "endian-note":
        return "memory.bin", struct.pack("<I", len(flag)) + flag.encode() + b"\x00" * 32
    if recipe == "hidden-files":
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w:gz") as archive:
            for name, content in {"workspace/README.txt": b"Inspect every file, including hidden entries.\n", "workspace/.config/training.txt": flag.encode()}.items():
                info = tarfile.TarInfo(name); info.size = len(content); info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
        return "workspace.tar.gz", data.getvalue()
    if recipe == "packet-courier":
        payload = flag.encode()
        udp = struct.pack("!HHHH", 40000, 31337, 8 + len(payload), 0) + payload
        ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 1, 0, 64, 17, 0, bytes([192, 0, 2, 10]), bytes([198, 51, 100, 20]))
        total = sum(struct.unpack("!10H", ip)); total = (total & 65535) + (total >> 16); total = (total & 65535) + (total >> 16)
        ip = ip[:10] + struct.pack("!H", (~total) & 65535) + ip[12:]
        packet = bytes.fromhex("0200000000020200000000010800") + ip + udp
        pcap = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
        return "courier.pcap", pcap + struct.pack("<IIII", 1700000000, 0, len(packet), len(packet)) + packet
    if recipe == "archive-layers":
        return "layers.zip", zip_bytes({"README.txt": "Decode payload.hex into text, then Base64-decode that text.\n", "payload.hex": encoded.encode().hex() + "\n"})
    raise ValueError("This exercise has no downloadable artifact")
