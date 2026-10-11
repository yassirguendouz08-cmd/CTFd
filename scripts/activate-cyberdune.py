"""Activate/restore the supplied CyberDune theme; run inside the CTFd container."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', choices=('core-theme', 'cyberdune'), default='core-theme', help='Theme to activate (default: supplied core-theme).')
    parser.add_argument('--clear-theme-injections', action='store_true', help='Back up and clear the old Theme Header/Footer CSS/JS.')
    parser.add_argument('--restore', metavar='BACKUP_JSON', help='Restore a previously saved theme configuration.')
    args = parser.parse_args()
    from CTFd import create_app
    from CTFd.utils import get_config, set_config
    from CTFd.cache import cache
    app = create_app()
    with app.app_context():
        keys = ('ctf_theme', 'theme_header', 'theme_footer', 'theme_settings')
        if args.restore:
            data = json.loads(Path(args.restore).read_text(encoding='utf-8'))
            if not all(key in data for key in keys):
                raise SystemExit('Not a CYBERDUNE theme configuration backup.')
            for key in keys:
                set_config(key, data[key])
            cache.clear()
            print('Previous theme configuration restored. Restart CTFd.')
            return
        if not app.config.get('THEME_FALLBACK'):
            raise SystemExit('Enable THEME_FALLBACK before activating this theme.')
        if get_config('ctf_theme') == args.theme and not args.clear_theme_injections:
            print(args.theme + ' is already active.')
            return
        # /var/uploads is writable and bind-mounted by the supplied Docker Compose config.
        backup_dir = Path(app.config['UPLOAD_FOLDER']) / 'cyberdune-backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        filename = 'theme-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'
        backup = backup_dir / filename
        backup.write_text(json.dumps({key: get_config(key) for key in keys}, indent=2), encoding='utf-8')
        backup.chmod(0o600)
        set_config('ctf_theme', args.theme)
        try:
            settings = json.loads(get_config('theme_settings') or '{}') or {}
        except (TypeError, json.JSONDecodeError):
            settings = {}
        if not isinstance(settings, dict):
            settings = {}
        settings['challenge_window_size'] = 'lg'
        set_config('theme_settings', json.dumps(settings))
        if args.clear_theme_injections:
            set_config('theme_header', '')
            set_config('theme_footer', '')
        cache.clear()
        print(args.theme + ' activated. Configuration backup:', backup)
        print('Restart CTFd and refresh your browser. Accounts, flags, files, pages and logo are unchanged.')

if __name__ == '__main__':
    main()
