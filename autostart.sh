#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
case "${1:-status}" in
 enable|disable|status) exec /usr/bin/python3 manage.py "${1:-status}" ;;
 *) echo 'Use enable, disable, or status'; exit 2 ;;
esac
