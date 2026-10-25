"""Read-only HTTP and local disk probe for a host monitoring system."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True, help='Public platform origin, e.g. https://ctf.example.org')
    parser.add_argument('--manager-health-url', help='Private manager healthcheck URL, reachable only from the monitor host')
    parser.add_argument('--disk', type=Path, default=Path('.'))
    parser.add_argument('--minimum-free-gb', type=float, default=2)
    args = parser.parse_args()
    results = []
    for name, url in [('platform', args.origin.rstrip('/') + '/healthcheck'), ('manager', args.manager_health_url)]:
        if not url:
            continue
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                body = response.read(1024).strip()
                ok = response.status == 200 and (name != 'platform' or body == b'OK')
            results.append({'check':name, 'ok':ok})
        except (OSError, urllib.error.URLError):
            results.append({'check':name, 'ok':False})
    try:
        free = shutil.disk_usage(args.disk).free
        results.append({'check':'disk', 'ok':free >= args.minimum_free_gb * 1024**3, 'free_bytes':free})
    except OSError:
        results.append({'check':'disk', 'ok':False})
    print(json.dumps({'ok':all(row['ok'] for row in results), 'checks':results}))
    return 0 if all(row['ok'] for row in results) else 1


if __name__ == '__main__':
    sys.exit(main())
