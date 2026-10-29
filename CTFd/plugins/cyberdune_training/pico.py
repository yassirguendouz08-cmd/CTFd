"""Adapted MIT-licensed examples from the official picoCTF/picoCTF repository.

Source pinned at 457347a54f20f634733c69457afe0503b69021e1.
Local difficulties are CyberDune's educational estimates, not Academy ratings.
"""
import hashlib
import io
import json
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SOURCE = "Licensed learning example · author and license credits are included with the exercise files"
PICO = [
    dict(slug="pico-ecb-1", name="ECB Challenge", category="Cryptography", difficulty="Easy", value=50, minutes=20,
         description="Inspect a fictional service export containing an AES key and ciphertext. Use the supplied mode and padding information to recover your account's flag. This is a source-review and decryption exercise, not a brute-force challenge.",
         hint="Read every exported field. Knowing the AES key changes the problem completely."),
    dict(slug="pico-sql-1", name="SQL Login", category="Web", difficulty="Medium", value=200, minutes=40,
         description="Download the fictional login sample and investigate how its SQL query handles input. Recover your account's flag using the offline files; the exercise never connects to this platform or any external service.",
         hint="Use a quote to test where input is inserted into the query, then complete the exercise only against the supplied local sample."),
]


def rows():
    for item in PICO:
        yield dict(item, recipe=item["slug"], kind="challenge", active=True, source=SOURCE)


def artifact(recipe, flag):
    files = {"LICENSE-picoCTF.txt": (Path(__file__).parent / "LICENSE-picoCTF.txt").read_bytes(),
             "SOURCE.txt": b"Adapted from https://github.com/picoCTF/picoCTF at commit 457347a54f20f634733c69457afe0503b69021e1.\nAuthor: Tim Becker, ForAllSecure. Copyright Carnegie Mellon University. MIT license included.\n"}
    if recipe == "pico-ecb-1":
        key = hashlib.sha256(("pico-ecb-example:" + flag).encode()).digest()[:16]
        padder = padding.PKCS7(128).padder()
        padded = padder.update(flag.encode()) + padder.finalize()
        encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
        files["service-export.json"] = json.dumps(dict(key=key.hex(), ciphertext=(encryptor.update(padded) + encryptor.finalize()).hex(), mode="AES-128-ECB", padding="PKCS7")).encode()
        files["README.txt"] = b"The original sample prints both KEY and MESSAGE. This adaptation exports them as hexadecimal and adds explicit PKCS7 padding for arbitrary token lengths. Recover your flag by decrypting the message.\n"
    else:
        files["login.py"] = b'''import sqlite3

def login(username, password):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(open("accounts.sql", encoding="utf-8").read())
    # Deliberately vulnerable query, isolated to this local teaching sample.
    query = f"SELECT name, flag FROM users WHERE name='{username}' AND password='{password}'"
    try:
        row = connection.execute(query).fetchone()
    except sqlite3.Error:
        row = None
    connection.close()
    return row["flag"] if row else None

if __name__ == "__main__":
    import getpass
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    result = login(username, password)
    print(result if result else "Login failed")
'''
        escaped = flag.replace("'", "''")
        files["accounts.sql"] = ("CREATE TABLE users (name TEXT, password TEXT, flag TEXT);\n"
            "INSERT INTO users VALUES ('guest', 'guest-password', 'not-the-flag');\n"
            "INSERT INTO users VALUES ('archive_admin', 'a-long-random-password', '" + escaped + "');\n").encode()
        files["README.txt"] = b"Run `python3 login.py` in this folder and investigate the source. The app uses only a fresh in-memory SQLite database loaded from accounts.sql. Try the SQL injection against this fictional sample only; it makes no network requests.\n"
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return recipe + ".zip", out.getvalue()
