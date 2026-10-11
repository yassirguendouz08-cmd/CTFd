#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  START) target=RUNNING ;;
  SOFTSTOP) target=STOPPED ;;
  *) printf 'Usage: bash scripts/vps-control.sh START|SOFTSTOP\n' >&2; exit 1 ;;
esac

instance=ocid1.instance.oc1.af-casablanca-1.ansholjrqm6tdtycwshrs36pb4sufd37lfpe4u7jvec5ujme5i2ymi2oph3q
region=af-casablanca-1
if command -v oci >/dev/null 2>&1; then
  cli=$(command -v oci)
elif [[ -x "$HOME/.local/share/cyberdune-oci/bin/oci" ]]; then
  cli="$HOME/.local/share/cyberdune-oci/bin/oci"
else
  printf 'OCI CLI is missing. Follow docs/VPS-CONTROL.md for the one-time setup.\n' >&2
  exit 1
fi

state=$("$cli" compute instance get --region "$region" --instance-id "$instance" \
  --query 'data."lifecycle-state"' --raw-output)
printf 'cyberdune-platform: %s\n' "$state"
if [[ "$state" == "$target" ]]; then
  printf 'Already %s; no action needed.\n' "$target"
  exit 0
fi
if [[ "$state" == TERMINATED || "$state" == TERMINATING ]]; then
  printf 'The instance is terminated or terminating; it cannot be started or stopped.\n' >&2
  exit 1
fi

printf 'Requesting %s. Waiting for %s (up to 10 minutes)...\n' "$1" "$target"
set +e
"$cli" compute instance action --region "$region" --instance-id "$instance" \
  --action "$1" --wait-for-state "$target" --max-wait-seconds 600 \
  --query 'data."lifecycle-state"' --raw-output
result=$?
set -e
if [[ "$result" == 2 ]]; then
  printf 'The wait timed out. Check Oracle Console; the requested action may still be in progress.\n' >&2
fi
exit "$result"
