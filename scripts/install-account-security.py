"""Scoped installer for the existing CyberDune VPS; run as root from Ubuntu home."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone

HOME = Path(__file__).resolve().parent
REPO = HOME / 'CTFd'
FILES = (
    'CTFd/auth.py',
    'CTFd/utils/email/providers/smtp.py',
    'CTFd/themes/core-theme/templates/confirm.html',
    'CTFd/plugins/cyberdune_security/__init__.py',
    'CTFd/plugins/cyberdune_security/templates/security_notice.html',
    'tests/test_cyberdune_security.py',
    'tests/test_cyberdune_instances.py',
    'docs/ACCOUNT-SECURITY.md',
)
if os.geteuid() != 0:
    raise SystemExit('Run with sudo.')
if not (REPO / 'CTFd/auth.py').is_file():
    raise SystemExit('Expected existing CTFd installation beside installer.')
backup = HOME / 'cyberdune-security-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup.mkdir(parents=True, exist_ok=False)
originals = {}
def replace(path, content):
    path = Path(path)
    originals[path] = path.read_bytes() if path.exists() else None
    saved = backup / str(path).lstrip('/')
    if path.exists():
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, saved)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(0o644)

try:
    with zipfile.ZipFile(HOME / 'account-security.zip') as archive:
        if set(archive.namelist()) != set(FILES):
            raise RuntimeError('Package file list differs from approved security scope')
        for name in FILES:
            content = archive.read(name)
            if name.endswith('.py'):
                ast.parse(content.decode('utf-8-sig'))
            replace(REPO / name, content)
    zones = b'limit_req_zone $binary_remote_addr zone=cyberdune_general:10m rate=20r/s;\nlimit_req_zone $binary_remote_addr zone=cyberdune_auth:10m rate=2r/s;\n'
    replace('/etc/nginx/conf.d/cyberdune-security.conf', zones)
    site = Path('/etc/nginx/sites-enabled/cyberdune').resolve()
    content = site.read_text()
    if '# CyberDune account protection' not in content:
        marker = '    location / {'
        if content.count(marker) != 1:
            raise RuntimeError('Unexpected Nginx layout; refusing an automatic edit')
        auth = '''    # CyberDune account protection
    limit_req zone=cyberdune_general burst=100 nodelay;
    limit_req_status 429;
    location ~ ^/(register|login|reset_password|confirm)(/|$) {
        limit_req zone=cyberdune_auth burst=12 nodelay;
        client_max_body_size 64k;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_read_timeout 30s;
    }

'''
        replace(site, content.replace(marker, auth + marker).encode())
    subprocess.run(['nginx','-t'],check=True)
except Exception:
    for path, previous in reversed(list(originals.items())):
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(previous)
    raise

code = """
import json
from pathlib import Path
from CTFd import create_app
from CTFd.utils import get_config, set_config
from CTFd.cache import clear_config
app=create_app()
with app.app_context():
    old={k:get_config(k) for k in ('cyberdune_https','password_min_length','verify_emails')}
    print('PREVIOUS_SECURITY_CONFIG='+json.dumps(old))
    set_config('cyberdune_https',True)
    set_config('password_min_length',max(12,int(old['password_min_length'] or 0)))
    clear_config()
    print('Email verification retained:',get_config('verify_emails'))
"""
result=subprocess.run(['docker','exec','-i','ctfd-ctfd-1','python'],input=code,text=True,check=True,capture_output=True)
for line in result.stdout.splitlines():
    if line.startswith('PREVIOUS_SECURITY_CONFIG='):
        (backup / 'security-config.json').write_text(line.split('=',1)[1])
    if line.startswith('Email verification retained:'):
        print(line)
subprocess.run(['systemctl','reload','nginx'],check=True)
subprocess.run(['docker','restart','ctfd-ctfd-1'],check=True)
print('Security files installed. Backup:',backup)
