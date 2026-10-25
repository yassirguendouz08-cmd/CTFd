"""Request, secret, account-link and queue retention regression coverage."""
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from CTFd.config import TestingConfig, gen_secret_key
from CTFd.utils.email import public_url_for
from tests.helpers import create_ctfd, destroy_ctfd


def test_signing_key_persists_and_unwritable_storage_fails(tmp_path):
    keyfile = tmp_path / 'secret'
    with patch.dict(os.environ, {'SECRET_KEY_FILE': str(keyfile)}):
        first = gen_secret_key()
        assert len(first) == 64
        assert gen_secret_key() == first
        assert keyfile.read_bytes() == first
    with patch('builtins.open', side_effect=PermissionError), patch('os.open', side_effect=PermissionError), pytest.raises(RuntimeError, match='persist'):
        gen_secret_key()


def test_request_body_and_multipart_limits_and_canonical_account_links():
    class Config(TestingConfig):
        MAX_CONTENT_LENGTH = 4096
        AUTH_MAX_CONTENT_LENGTH = 1024
        MAX_FORM_PARTS = 4
        PUBLIC_ORIGIN = 'https://ctf.example.test'

    app = create_ctfd(config=Config)
    try:
        client = app.test_client()
        response = client.post('/login', data={'name':'x' * 1500, 'password':'no'})
        assert response.status_code == 413
        client.get('/login')
        with client.session_transaction() as session:
            nonce = session['nonce']
        response = client.post('/login', data={'nonce':nonce,'name':'test','password':'no','one':'a','two':'b'}, content_type='multipart/form-data')
        assert response.status_code == 413
        with app.test_request_context('/', headers={'Host':'attacker.example'}):
            assert public_url_for('auth.reset_password', data='synthetic-token') == 'https://ctf.example.test/reset_password/synthetic-token'
        app.config['PUBLIC_ORIGIN'] = 'https://attacker.example@ctf.example.test'
        with app.test_request_context('/'), pytest.raises(ValueError):
            public_url_for('auth.reset_password')
    finally:
        destroy_ctfd(app)


def test_builder_retention_preserves_active_jobs_and_external_paths(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'services/instance-builder/worker.py'
    spec = importlib.util.spec_from_file_location('audit_builder', path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    root = tmp_path / 'jobs'
    root.mkdir()
    for name, state in [('a' * 32, 'ready'), ('b' * 32, 'failed'), ('c' * 32, 'building')]:
        folder = root / name
        folder.mkdir()
        status = folder / 'status.json'
        status.write_text(json.dumps({'state':state}))
        os.utime(status, (1,1))
    outside = tmp_path / 'outside'
    outside.mkdir()
    (root / ('d' * 32)).symlink_to(outside, target_is_directory=True)
    assert worker.cleanup_jobs(root, retention_days=7, now=1000000) == 2
    assert (root / ('c' * 32)).exists()
    assert outside.exists()
