"""Archive boundaries and the admin ZIP -> build -> instance creation workflow."""
import io
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from CTFd.config import TestingConfig
from CTFd.models import db
from tests.helpers import create_ctfd, gen_user, login_as_user

spec = importlib.util.spec_from_file_location('archive_checks', Path(__file__).resolve().parents[1] / 'CTFd/plugins/ctfd_chall_manager/zip_archive.py')
archive_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive_module)
extract_archive, inspect_archive = archive_module.extract_archive, archive_module.inspect_archive


def archive(files=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as zipped:
        for name, content in (files or {'app/Dockerfile': 'FROM python:3.11-slim-bookworm\nEXPOSE 8080\n', 'app/app.py': 'print("example")'}).items():
            zipped.writestr(name, content)
    stream.seek(0)
    return stream


class TestArchives(unittest.TestCase):
    def test_context_port_and_extraction(self):
        stream = archive({'example/Dockerfile': 'FROM python:3.11-slim-bookworm\nEXPOSE 5000/tcp\n', 'example/app.py': 'print(1)'})
        self.assertEqual(inspect_archive(stream), {'context': 'example', 'port': 5000})
        with tempfile.TemporaryDirectory() as directory:
            context = extract_archive(stream, directory)
            self.assertEqual(context.name, 'example')
            self.assertEqual((context / 'app.py').read_text(), 'print(1)')

    def test_rejects_unsafe_or_ambiguous_archives(self):
        for files in [{'../escape': 'x', 'Dockerfile': 'FROM alpine'},
                      {'C:\\escape': 'x', 'Dockerfile': 'FROM alpine'},
                      {'app.py': 'x'}, {'Dockerfile': 'FROM alpine', 'other/Dockerfile': 'FROM alpine'}]:
            with self.subTest(files=list(files)), self.assertRaises(ValueError):
                inspect_archive(archive(files))

    def test_rejects_symlink(self):
        stream = archive({'Dockerfile': 'FROM alpine'})
        with zipfile.ZipFile(stream, 'a') as zipped:
            link = zipfile.ZipInfo('link')
            link.external_attr = (0o120777 << 16)
            zipped.writestr(link, '../../outside')
        with self.assertRaises(ValueError):
            inspect_archive(stream)


class TestZipWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        class Config(TestingConfig):
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            SAFE_MODE = False
            SERVER_NAME = None
            UPLOAD_FOLDER = cls.temp.name
        cls.app = create_ctfd(enable_plugins=True, config=Config)
        cls.admin = login_as_user(cls.app, name='admin', password='password')
        with cls.admin.session_transaction() as session:
            cls.nonce = session['nonce']
        with cls.app.app_context():
            gen_user(db, name='zip-player', email='zip@example.test')
        cls.player = login_as_user(cls.app, name='zip-player', password='password')
        cls.queue = Path(cls.temp.name) / 'instance-builds'
        cls.queue.mkdir()
        (cls.queue / 'heartbeat').touch()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_full_workflow_and_retry_is_idempotent(self):
        from CTFd.plugins.ctfd_chall_manager.models import DynamicIaCChallenge
        from CTFd.plugins.ctfd_chall_manager.utils.chall_manager_error import ChallManagerException
        base = '/plugins/ctfd-chall-manager/admin/zip'
        self.assertEqual(self.admin.get('/admin/challenges/new').status_code, 200)
        self.assertIn(b'Upload instance ZIP', self.admin.get('/admin/challenges/new').data)
        self.assertEqual(self.player.get(base + '/new').status_code, 302)
        response = self.admin.post(base + '/new', data={'nonce': self.nonce, 'archive': (archive(), 'Uploaded.zip'), 'points': '150', 'category': 'Web'}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 302)
        job = response.location.rsplit('/', 1)[-1]
        folder = self.queue / job
        payload = json.loads((folder / 'request.json').read_text())['payload']
        self.assertEqual(payload['name'], 'Uploaded')
        self.assertEqual(payload['additional']['port'], '8080')
        self.assertEqual(payload['state'], 'hidden')
        self.assertEqual(len(payload['additional']['flag_seed']), 64)
        self.assertEqual(self.player.get(base + '/' + job + '/status').status_code, 302)
        self.assertNotIn(b'flag_seed', self.admin.get(base + '/' + job + '/status').data)
        self.assertEqual(self.admin.post(base + '/' + job + '/finish', data={'nonce': self.nonce}).status_code, 409)
        (folder / 'status.json').write_text(json.dumps({'state': 'ready', 'message': 'Built'}))
        with patch('CTFd.plugins.ctfd_chall_manager.models.create_challenge', side_effect=ChallManagerException()), patch('CTFd.plugins.ctfd_chall_manager.models.get_challenge'), patch('CTFd.plugins.ctfd_chall_manager.models.delete_challenge'):
            self.assertEqual(self.admin.post(base + '/' + job + '/finish', data={'nonce': self.nonce}).status_code, 502)
        with patch('CTFd.plugins.ctfd_chall_manager.models.create_challenge') as create:
            first = self.admin.post(base + '/' + job + '/finish', data={'nonce': self.nonce})
            self.assertEqual(first.status_code, 200, first.data)
            second = self.admin.post(base + '/' + job + '/finish', data={'nonce': self.nonce})
            self.assertEqual(second.get_json(), first.get_json())
            self.assertEqual(create.call_count, 1)
            with self.app.app_context():
                self.assertEqual(DynamicIaCChallenge.query.count(), 1)

    def test_invalid_archive_and_offline_worker(self):
        base = '/plugins/ctfd-chall-manager/admin/zip/new'
        response = self.admin.post(base, data={'nonce': self.nonce, 'archive': (archive({'../oops': 'bad'}), 'Bad.zip')}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        marker = self.queue / 'heartbeat'
        os.utime(marker, (1, 1))
        try:
            response = self.admin.post(base, data={'nonce': self.nonce, 'archive': (archive(), 'Good.zip')}, content_type='multipart/form-data')
            self.assertEqual(response.status_code, 400)
            self.assertIn(b'offline', response.data)
        finally:
            marker.touch()
