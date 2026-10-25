"""Single Docker build worker for the admin-only upload queue."""
import argparse
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'CTFd/plugins/ctfd_chall_manager'))
from zip_archive import MAX_EXTRACTED_BYTES, extract_archive


def cleanup_jobs(root, retention_days=7, now=None):
    """Remove only expired, finished queue jobs; retain images used by challenges."""
    cutoff = (time.time() if now is None else now) - retention_days * 86400
    removed = 0
    for folder in Path(root).iterdir():
        if (folder.is_symlink() or not folder.is_dir() or len(folder.name) != 32
                or any(c not in '0123456789abcdef' for c in folder.name)):
            continue
        status = folder / 'status.json'
        try:
            if status.is_symlink() or status.stat().st_mtime >= cutoff:
                continue
            if json.loads(status.read_text()).get('state') not in ('ready', 'failed'):
                continue
        except (OSError, ValueError, AttributeError):
            continue
        shutil.rmtree(folder)
        removed += 1
    return removed


def write_status(folder, state, message, uid, gid):
    temporary = folder / 'status.tmp'
    temporary.write_text(json.dumps({'state': state, 'message': message}), encoding='utf-8')
    os.chown(temporary, uid, gid)
    temporary.chmod(0o640)
    temporary.replace(folder / 'status.json')


def build(folder, uid, gid):
    write_status(folder, 'building', 'Building your challenge image…', uid, gid)
    context_root = folder / 'context'
    log_path = folder / 'build.log'
    process = None
    try:
        if shutil.disk_usage(folder).free < MAX_EXTRACTED_BYTES + 512 * 1024 * 1024:
            raise ValueError('Not enough free disk space to build safely. Ask an administrator to free space.')
        request = json.loads((folder / 'request.json').read_text())
        image = request['payload']['additional']['image']
        if image != f'cyberdune/zip-{folder.name}:v1':
            raise ValueError('Invalid build image name.')
        context = extract_archive(folder / 'challenge.zip', context_root)
        with log_path.open('wb') as log:
            os.chown(log_path, uid, gid)
            log_path.chmod(0o640)
            process = subprocess.Popen(
                ['docker', 'build', '--pull=false', '--tag', image, str(context)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
                env=dict(os.environ, DOCKER_BUILDKIT='1'))
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            started, written = time.monotonic(), 0
            while selector.get_map():
                if time.monotonic() - started > 900:
                    raise ValueError('The build exceeded 15 minutes. Check the Dockerfile and try again.')
                for key, _ in selector.select(timeout=1):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    written += len(chunk)
                    if written > 10 * 1024 * 1024:
                        raise ValueError('The build produced too much output. Check the Dockerfile.')
                    log.write(chunk)
                    log.flush()
            selector.close()
            result = process.wait(timeout=10)
        if result:
            raise ValueError('Docker could not build this ZIP. See the build log below and upload a corrected ZIP.')
        write_status(folder, 'ready', 'Image built. Creating the instance challenge…', uid, gid)
    except Exception as exc:
        if process and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        write_status(folder, 'failed', str(exc), uid, gid)
    finally:
        if context_root.exists() and context_root.resolve().parent == folder.resolve():
            shutil.rmtree(context_root)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--jobs', type=Path, required=True)
    parser.add_argument('--uid', type=int, required=True)
    parser.add_argument('--gid', type=int, required=True)
    parser.add_argument('--retention-days', type=int, default=7)
    args = parser.parse_args()
    if args.retention_days < 1:
        parser.error('--retention-days must be at least 1')
    args.jobs.mkdir(parents=True, exist_ok=True)
    os.chown(args.jobs, args.uid, args.gid)
    args.jobs.chmod(0o750)

    def heartbeat():
        while True:
            marker = args.jobs / 'heartbeat'
            marker.touch()
            os.chown(marker, args.uid, args.gid)
            marker.chmod(0o640)
            time.sleep(2)

    for status_path in args.jobs.glob('*/status.json'):
        try:
            if json.loads(status_path.read_text()).get('state') == 'building':
                write_status(status_path.parent, 'failed', 'The builder restarted during this build. Please upload the ZIP again.', args.uid, args.gid)
        except (OSError, ValueError, AttributeError):
            continue
    threading.Thread(target=heartbeat, daemon=True).start()
    last_cleanup = 0
    while True:
        if time.monotonic() - last_cleanup >= 3600:
            cleanup_jobs(args.jobs, args.retention_days)
            last_cleanup = time.monotonic()
        for request in sorted(args.jobs.glob('*/request.json'), key=lambda p: p.stat().st_mtime):
            if len(request.parent.name) != 32 or any(c not in '0123456789abcdef' for c in request.parent.name):
                continue
            if not (request.parent / 'status.json').exists():
                build(request.parent, args.uid, args.gid)
        time.sleep(2)


if __name__ == '__main__':
    main()
