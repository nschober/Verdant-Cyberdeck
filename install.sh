#!/usr/bin/env bash
# Unified source/deb setup. A bare invocation inspects; installation is explicit.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
exec /usr/bin/python3 scripts/setup_package.py "$@"
