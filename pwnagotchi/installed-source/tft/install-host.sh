#!/bin/bash
# Install dependencies only. Does not invoke upstream's system-file installer.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ $EUID -ne 0 ]]; then
    echo 'Run: sudo bash /root/pwnagotchi-modern/tft/install-host.sh' >&2
    exit 1
fi
if [[ $(uname -m) != aarch64 ]]; then
    echo 'This installer targets the aarch64 Pi.' >&2
    exit 1
fi
exec 9>/run/pwnagotchi-modern-install.lock
flock -n 9 || { echo 'Another installation is running.' >&2; exit 1; }
apt-get update
apt-get install -y python3-venv build-essential pkg-config swig \
    libdbus-1-dev libglib2.0-dev libcap-dev libffi-dev libssl-dev \
    fonts-dejavu-core
python3 -m venv .bootstrap
.bootstrap/bin/python -m pip install --upgrade pip uv
.bootstrap/bin/uv python install 3.11
if [[ ! -e .venv/bin/python ]]; then
    .bootstrap/bin/uv venv --python 3.11 .venv
fi
if ! .venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 11)'; then
    echo 'Existing .venv is not Python 3.11; preserve it and choose another installation folder.' >&2
    exit 1
fi
.bootstrap/bin/uv pip install --python .venv/bin/python \
    --only-binary torch --only-binary torchvision \
    -r tft/requirements-modern.txt
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
.venv/bin/python tft/test_backend.py
.venv/bin/python tft/smoke-ai.py
.venv/bin/python bin/pwnagotchi --help >/dev/null
.bootstrap/bin/uv pip freeze --python .venv/bin/python >tft/installed-requirements.txt
echo 'Runtime installed; TFT backend, synthetic AI and CLI checks passed.'
echo 'No Wi-Fi interface or running service was changed. Live integration is still pending.'
