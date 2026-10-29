"""Adapted MIT-licensed examples from the official picoCTF/picoCTF repository.

Source pinned at 457347a54f20f634733c69457afe0503b69021e1.
Local difficulties are CyberDune's educational estimates, not Academy ratings.
"""
import hashlib
import io
import json
import sqlite3
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
         description="Find the query flaw in a fictional login and bypass it in the isolated lab. Each request uses a disposable SQLite database containing one fictional user; it has no connection to platform accounts or the CTF database.",
         hint="Look at how quotes in the input change the structure of the query. Use the provided lab only."),
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
        files["login.php"] = b'''<?php
// Query reproduced for study; use CyberDune's isolated lab.
$username = $_POST["username"];
$password = $_POST["password"];
$query = "SELECT * FROM users WHERE name='$username' AND password='$password'";
// Original sample returns the flag if the query matches a user.
?>
'''
        files["README.txt"] = b"Use the isolated login form on the challenge page. The lab reproduces the sample's vulnerable SQL concatenation on a fresh in-memory database with fictional credentials. No real account login is involved.\n"
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return recipe + ".zip", out.getvalue()


def check_sql_login(username, password):
    """Evaluate one bounded SELECT on a disposable, private in-memory database."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.enable_load_extension(False)
        connection.execute("CREATE TABLE users (name TEXT, password TEXT)")
        connection.execute("INSERT INTO users VALUES (?, ?)", ("fictional-admin", hashlib.sha256(b"not-a-platform-password").hexdigest()))
        connection.execute("PRAGMA query_only=ON")
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 4096)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 1024)
        connection.set_progress_handler(lambda: 1, 5000)

        def authorize(action, arg1, arg2, database, trigger):
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ and arg1 == "users":
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        connection.set_authorizer(authorize)
        # Deliberately vulnerable query ONLY inside this standalone teaching DB.
        query = f"SELECT * FROM users WHERE name='{username}' AND password='{password}'"
        try:
            return connection.execute(query).fetchone() is not None
        except sqlite3.Error:
            return False
    finally:
        connection.close()
