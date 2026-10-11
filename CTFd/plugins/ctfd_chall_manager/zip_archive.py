"""Shared archive validation for the admin upload and isolated build queue."""
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 250 * 1024 * 1024


def inspect_archive(source):
    try:
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > 2000:
                raise ValueError('The ZIP must contain between 1 and 2000 files.')
            total = 0
            names = set()
            dockerfiles = []
            for entry in entries:
                name = entry.filename.replace('\\', '/')
                path = PurePosixPath(name)
                mode = entry.external_attr >> 16
                if (not path.parts or path.is_absolute() or '..' in path.parts or ':' in name
                        or '\x00' in name or stat.S_ISLNK(mode) or entry.flag_bits & 1):
                    raise ValueError('The ZIP contains an unsafe path, link, or encrypted file.')
                if str(path) in names:
                    raise ValueError('The ZIP contains duplicate paths.')
                names.add(str(path))
                total += entry.file_size
                if total > MAX_EXTRACTED_BYTES:
                    raise ValueError('The unpacked challenge exceeds 250 MB.')
                if path.name == 'Dockerfile' and not entry.is_dir():
                    dockerfiles.append(entry)
            if len(dockerfiles) != 1:
                raise ValueError('Include exactly one Dockerfile, at the ZIP root or inside one challenge folder.')
            dockerfile = dockerfiles[0]
            if dockerfile.file_size > 256 * 1024:
                raise ValueError('The Dockerfile is too large.')
            text = archive.read(dockerfile).decode('utf-8-sig')
            exposed = re.search(r'^\s*EXPOSE\s+(\d+)(?:/tcp)?\b', text, re.M | re.I)
            port = int(exposed[1]) if exposed else 8080
            if not 1 <= port <= 65535:
                raise ValueError('The Dockerfile EXPOSE port is invalid.')
            return {'context': str(PurePosixPath(dockerfile.filename.replace('\\', '/')).parent), 'port': port}
    except (zipfile.BadZipFile, UnicodeError, RuntimeError) as exc:
        raise ValueError('Upload a readable ZIP containing a Dockerfile.') from exc


def extract_archive(source, destination):
    info = inspect_archive(source)
    destination = Path(destination).resolve()
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            target = (destination / entry.filename.replace('\\', '/')).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('Invalid archive path.')
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as src, target.open('wb') as dst:
                    import shutil
                    shutil.copyfileobj(src, dst)
                target.chmod(0o644 | ((entry.external_attr >> 16) & 0o111))
    return destination / info['context']
