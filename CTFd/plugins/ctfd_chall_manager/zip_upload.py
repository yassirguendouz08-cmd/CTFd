"""Admin-only ZIP creation through a file queue; CTFd never controls Docker."""
import json
import re
import time
import uuid
from pathlib import Path

from flask import abort, current_app, jsonify, redirect, render_template, request, url_for
from CTFd.cache import clear_challenges
from CTFd.exceptions.challenges import ChallengeCreateException
from CTFd.plugins.ctfd_chall_manager.models import DynamicIaCChallenge, DynamicIaCValueChallenge
from CTFd.plugins.ctfd_chall_manager.utils.lock import load_or_store
from CTFd.plugins.ctfd_chall_manager.web_preset import web_payload
from CTFd.plugins.ctfd_chall_manager.zip_archive import MAX_ZIP_BYTES, inspect_archive
from CTFd.utils.decorators import admins_only


def queue_root():
    return Path(current_app.config['UPLOAD_FOLDER']) / 'instance-builds'


def worker_ready():
    try:
        return time.time() - (queue_root() / 'heartbeat').stat().st_mtime < 30
    except OSError:
        return False


def read_job(job_id):
    if not re.fullmatch(r'[0-9a-f]{32}', job_id):
        abort(404)
    folder = queue_root() / job_id
    try:
        data = json.loads((folder / 'request.json').read_text())
    except (OSError, ValueError):
        abort(404)
    return folder, data


def job_status(folder):
    try:
        state = json.loads((folder / 'status.json').read_text())
    except (OSError, ValueError):
        state = {'state': 'queued', 'message': 'Waiting for the builder.'}
    try:
        with (folder / 'build.log').open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 32000))
            state['log'] = stream.read().decode('utf-8', errors='replace')
    except OSError:
        state['log'] = ''
    return state


def recent_builds():
    if not queue_root().exists():
        return []
    builds = []
    for path in sorted(queue_root().glob('*/request.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
        try:
            data = json.loads(path.read_text())
            builds.append({'id': path.parent.name, 'name': data['payload']['name'],
                           'state': job_status(path.parent)['state']})
        except (OSError, ValueError, KeyError):
            continue
    return builds


def register_zip_upload(blueprint):
    @blueprint.app_context_processor
    def zip_upload_context():
        return {'InstanceZipUploadEnabled': True}

    @blueprint.before_request
    def limit_zip_upload():
        if (request.endpoint == 'ctfd-chall-manager.new_zip_challenge'
                and request.content_length and request.content_length > MAX_ZIP_BYTES + 1024 * 1024):
            return 'The ZIP must be 50 MB or smaller.', 413

    @blueprint.route('/admin/zip/new', methods=['GET', 'POST'])
    @admins_only
    def new_zip_challenge():
        values = {key: request.form.get(key, default) for key, default in
                  {'name': '', 'category': 'Web', 'description': '', 'points': '100', 'port': ''}.items()}
        error, status = None, 200
        if request.method == 'POST':
            folder = None
            try:
                if not worker_ready():
                    raise ValueError('The builder is offline. Please try again when it is available.')
                upload = request.files.get('archive')
                if not upload or not upload.filename.lower().endswith('.zip'):
                    raise ValueError('Choose a challenge ZIP file.')
                job_id = uuid.uuid4().hex
                folder = queue_root() / job_id
                folder.mkdir(mode=0o750, parents=True)
                archive_path = folder / 'challenge.zip'
                with archive_path.open('wb') as dst:
                    size = 0
                    while True:
                        chunk = upload.stream.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > MAX_ZIP_BYTES:
                            raise ValueError('The ZIP must be 50 MB or smaller.')
                        dst.write(chunk)
                info = inspect_archive(archive_path)
                values['name'] = values['name'].strip() or Path(upload.filename).stem[:128]
                values['port'] = values['port'].strip() or str(info['port'])
                payload = web_payload(dict(values, image=f'cyberdune/zip-{job_id}:v1'))
                category = values['category'].strip() or 'Web'
                if len(category) > 128:
                    raise ValueError('The category must be 128 characters or fewer.')
                payload['category'] = category
                payload['additional']['build_job'] = job_id
                # Publish request last: the worker cannot see a partial upload.
                temporary = folder / 'request.tmp'
                temporary.write_text(json.dumps({'payload': payload}), encoding='utf-8')
                temporary.chmod(0o600)
                temporary.replace(folder / 'request.json')
                return redirect(url_for('ctfd-chall-manager.zip_build', job_id=job_id))
            except ValueError as exc:
                error, status = str(exc), 400
                if folder:
                    import shutil
                    shutil.rmtree(folder)
        return render_template('chall_manager_zip_new.html', values=values, error=error,
                               worker_ready=worker_ready(), recent_builds=recent_builds()), status

    @blueprint.route('/admin/zip/<job_id>')
    @admins_only
    def zip_build(job_id):
        folder, data = read_job(job_id)
        return render_template('chall_manager_zip_build.html', job_id=job_id,
                               name=data['payload']['name'], status=job_status(folder))

    @blueprint.route('/admin/zip/<job_id>/status')
    @admins_only
    def zip_build_status(job_id):
        folder, _ = read_job(job_id)
        return jsonify(job_status(folder))

    @blueprint.route('/admin/zip/<job_id>/finish', methods=['POST'])
    @admins_only
    def finish_zip_build(job_id):
        folder, data = read_job(job_id)
        if job_status(folder)['state'] != 'ready':
            return jsonify(error='The build has not completed successfully.'), 409
        lock = load_or_store('zip-challenge-' + job_id)
        lock.lock()
        try:
            existing = next((c for c in DynamicIaCChallenge.query.all()
                             if (c.additional or {}).get('build_job') == job_id), None)
            if existing is None:
                try:
                    existing = DynamicIaCValueChallenge.create_from_data(data['payload'])
                except ChallengeCreateException:
                    return jsonify(error='The image is built, but instance registration failed. You can retry without rebuilding.'), 502
                clear_challenges()
            return jsonify(url=url_for('admin.challenges_detail', challenge_id=existing.id))
        finally:
            lock.unlock()
