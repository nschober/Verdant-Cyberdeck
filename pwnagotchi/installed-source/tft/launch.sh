#!/bin/bash
set -euo pipefail
cd /root/pwnagotchi-modern
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
# Honor mode changes requested through the standard Web UI.
if [[ -e /root/.pwnagotchi-auto ]]; then
    printf 'auto\n' > /etc/pwnagotchi/mode
    rm -f /root/.pwnagotchi-auto /root/.pwnagotchi-manual
elif [[ -e /root/.pwnagotchi-manual ]]; then
    printf 'manual\n' > /etc/pwnagotchi/mode
    rm -f /root/.pwnagotchi-manual
fi
mode=$(cat /etc/pwnagotchi/mode)
case "$mode" in
    manual) exec .venv/bin/python bin/pwnagotchi --manual ;;
    auto) exec .venv/bin/python bin/pwnagotchi ;;
    *) echo "Invalid mode in /etc/pwnagotchi/mode: $mode" >&2; exit 1 ;;
esac
