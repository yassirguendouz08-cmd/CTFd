"""Prepare four distinct supplied exercises. Keep generated output outside Git."""
import argparse
import base64
import gzip
import hashlib
import io
import json
import re
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

PACK = "drive-training-v1"
FLAG = re.compile(rb"CYBERDUNE\{[^}\r\n]+\}")
REPO = Path(__file__).resolve().parents[2]
CATALOGUE = REPO / "CTFd/utils/challenge_localization/drive-training.json"


def one_flag(data):
    found = set(FLAG.findall(data))
    if len(found) != 1:
        raise ValueError("Expected one unambiguous flag in the selected evidence.")
    return found.pop().decode("ascii")


def archive_bytes(files):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for name, data in sorted(files.items()):
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts or "\\" in name:
                    raise ValueError("Unsafe archive path.")
                item = tarfile.TarInfo(name)
                item.size, item.mode, item.mtime = len(data), 0o644, 0
                archive.addfile(item, io.BytesIO(data))
    return buffer.getvalue()


def build(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == REPO or REPO in output.parents:
        raise ValueError("Generated flags and player evidence must stay outside the Git repository.")
    if output.exists():
        raise ValueError("Output exists. Reuse its private manifest; do not overwrite imported evidence.")
    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    with zipfile.ZipFile(source) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate ZIP entries.")
        for entry in archive.infolist():
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in entry.filename:
                raise ValueError("Unsafe input path.")
            if entry.file_size > 16 * 1024 * 1024:
                raise ValueError("Unexpectedly large input entry.")

        hello = archive.read("hello_chalenge/hello.txt")
        number = re.search(rb"\b[0-9]{5,}\b", hello)
        if not number:
            raise ValueError("Missing decimal input.")
        computed = "CYBERDUNE{" + format(int(number[0]), "x") + "}"
        original_hello_answer = one_flag(archive.read("hello_chalenge/soulution"))
        if computed.lower() != original_hello_answer.lower():
            raise ValueError("The supplied hexadecimal answer disagrees with the exercise.")

        hidden = {
            e.filename: archive.read(e)
            for e in archive.infolist()
            if e.filename.startswith("linux_easyyy-lab/") and not e.is_dir()
            and "soulution" not in e.filename.lower()
        }
        if len(hidden) != 3:
            raise ValueError("Expected the hidden file and two visible distractions.")
        hidden_answer = one_flag(hidden["linux_easyyy-lab/.real_flag.txt"])
        maze = {
            e.filename: archive.read(e)
            for e in archive.infolist()
            if e.filename.startswith("linux_lab-easy/") and not e.is_dir()
            and "soulution" not in e.filename.lower()
        }
        if len(maze) != 2801:
            raise ValueError("The archive maze does not match the supplied exercise.")
        clue = maze["linux_lab-easy/FLAG HERE/documents/backup/flag/real_flag.txt"]
        maze_answer = one_flag(base64.b64decode(clue.strip(), validate=True))

        log = archive.read("linux_lab_meudiem/server.log")
        secrets = re.findall(rb"SECRET_KEY[=:]\s*([A-Za-z0-9+/=]+)", log)
        if len(secrets) != 1:
            raise ValueError("Expected a single SECRET_KEY entry.")
        log_answer = one_flag(base64.b64decode(secrets[0], validate=True))

    exercises = [
        ("hello-hex", "Crypto", original_hello_answer, "hello.txt", hello, "hello_chalenge"),
        ("hidden-file", "Linux", hidden_answer, "hidden-file.tar.gz", archive_bytes(hidden), "linux_easyyy-lab"),
        ("archive-maze", "Linux", maze_answer, "archive-maze.tar.gz", archive_bytes(maze), "linux_lab-easy"),
        ("needle-log", "Linux", log_answer, "server.log", log, "linux_lab_meudiem"),
    ]
    if len({row[2] for row in exercises}) != 4:
        raise ValueError("Duplicate answers remain after deduplication.")
    output.mkdir(parents=True)
    manifest = {"pack": PACK, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "omitted_variants": ["linux_lab.rar", "linux_lab_2.zip"], "challenges": []}
    for slug, category, answer, filename, content, original in exercises:
        public = catalogue[slug]["fr"]
        if answer in json.dumps(catalogue[slug], ensure_ascii=False):
            raise ValueError("A public translation contains the answer.")
        folder = output / slug
        folder.mkdir()
        (folder / filename).write_bytes(content)
        manifest["challenges"].append({
            "slug": slug, "name": public["name"], "category": category, "value": 100,
            "description": public["description"], "hints": public["hints"], "flag": answer,
            "flag_data": "case_insensitive" if slug == "hello-hex" else "", "files": [f"{slug}/{filename}"], "source_folder": original,
            "sha256": {filename: hashlib.sha256(content).hexdigest()},
        })
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Prepared 4 distinct private exercises; original flags preserved; solutions excluded. No flags printed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.source, args.output)
