"""Select the locally published launcher for future admin ZIP/image creations."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
reference = sys.argv[1]
if not re.fullmatch(r'scenario-registry:5000/scenarios/web-container:v2-(amd64|arm64)@sha256:[0-9a-f]{64}', reference):
    raise SystemExit('Invalid local launcher reference')
from CTFd import create_app
from CTFd.utils import set_config
from CTFd.cache import cache
app = create_app()
with app.app_context():
    set_config('chall-manager:web_scenario', reference)
    cache.clear()
print('New ZIP challenges will use the verified v2 launcher.')
