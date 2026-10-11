#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Local changes found. Commit them or stash them before updating." >&2
  git status --short
  exit 1
fi

git pull --ff-only origin master
bash scripts/start-cyberdune.sh
docker compose restart ctfd
echo "CyberDune updated. Open forwarded port 80 and refresh with Ctrl+Shift+R."
