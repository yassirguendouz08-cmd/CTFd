"""Install the theme-only CYBERDUNE redesign, retaining a complete file rollback."""
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone

HOME=Path(__file__).resolve().parent
REPO=HOME/'CTFd'
if os.geteuid()!=0:
    raise SystemExit('Run with sudo.')
if not (REPO/'CTFd/themes/core-theme/templates/base.html').is_file():
    raise SystemExit('Expected existing CyberDune CTFd checkout beside this installer.')
backup=HOME/'cyberdune-theme-backups'/('redesign-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
backup.mkdir(parents=True,exist_ok=False)
changed=[]
try:
    with zipfile.ZipFile(HOME/'ui-redesign.zip') as archive:
        for name in archive.namelist():
            allowed=name.startswith('CTFd/themes/core-theme/') or name=='docs/UI-REDESIGN.md' or name.startswith('docs/redesign-font-licenses/')
            target=(REPO/name).resolve()
            if not allowed or '..' in Path(name).parts or not target.is_relative_to(REPO.resolve()):
                raise RuntimeError('Package contains an unexpected path')
            original=target.read_bytes() if target.exists() else None
            changed.append((target,original))
            saved=backup/name
            if original is not None:
                saved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(target,saved)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.read(name))
            target.chmod(0o644)
    (backup/'new-files.txt').write_text('\n'.join(str(path.relative_to(REPO)) for path,previous in changed if previous is None))
    code="""
from CTFd import create_app
app=create_app()
with app.app_context():
    for name in ('base.html','pagehome.html','login.html','register.html','reset_password.html','confirm.html','challenges.html','challenge.html','scoreboard.html','settings.html','users/private.html','users/public.html','teams/private.html','teams/public.html'):
        app.jinja_env.get_template(name)
print('Theme templates compiled successfully')
"""
    result=subprocess.run(['docker','exec','-i','ctfd-ctfd-1','python'],input=code,text=True,capture_output=True)
    if result.returncode:
        raise RuntimeError('Template validation failed: '+result.stderr[-2500:])
    print('Theme templates compiled successfully')
    subprocess.run(['docker','restart','ctfd-ctfd-1'],check=True)
except Exception:
    for path,previous in reversed(changed):
        if previous is None: path.unlink(missing_ok=True)
        else: path.write_bytes(previous)
    raise
print('Theme-only redesign installed. Backup:',backup)
