#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == --help && $# -eq 1 ]]; then
    echo 'Usage: bash install.sh'
    echo 'Install Verdant Cyberdeck for the current Kali ARM64 desktop user.'
    exit 0
fi
if (( $# != 0 )); then
    echo 'Usage: bash install.sh' >&2
    exit 2
fi
if (( EUID == 0 )); then
    echo 'Run this installer as your desktop user. It uses sudo only for apt.' >&2
    exit 1
fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mkdir -p logs
exec > >(tee -a logs/install.log) 2>&1
trap 'echo "Installation failed at line $LINENO (exit $?)"' ERR
. /etc/os-release
echo "OS: $PRETTY_NAME; machine: $(uname -m); packages: $(dpkg --print-architecture)"
[[ "$ID" == kali && "$(dpkg --print-architecture)" == arm64 ]] || { echo 'This installation targets Kali ARM64'; exit 1; }
echo "Graphics session: DISPLAY=${DISPLAY:-unset}, WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset}, XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-unset}"
if [[ -n "${DISPLAY:-}" ]]; then
    xrandr --current || echo 'Display inaccessible; hardware startup remains unverified'
fi
runtime_packages=(python3 python3-tk python3-pil python3-pil.imagetk python3-evdev fonts-dejavu-core)
missing=()
for package in "${runtime_packages[@]}"; do
    if [[ "$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null)" != 'install ok installed' ]]; then
        missing+=("$package")
    fi
done
if (( ${#missing[@]} )); then
    sudo apt-get --no-remove install "${missing[@]}"
fi
/usr/bin/python3 -c 'import tkinter; from PIL import Image, ImageTk; import evdev'
/usr/bin/python3 -c 'from cyberdeck.system_status import graphics; print(graphics())'
for file in cyberdeck/main.py cyberdeck/dashboard.py cyberdeck/pwnagotchi.py run.sh autostart.sh uninstall.sh; do
    test -s "$file"
done
chmod +x run.sh install.sh install-tools.sh autostart.sh uninstall.sh
/usr/bin/python3 -m compileall -q cyberdeck manage.py
./run.sh --self-test
if [[ -n "${DISPLAY:-}" ]]; then
    ./run.sh --smoke-test
else
    echo 'Desktop startup unavailable in this terminal. Offscreen startup passed; physical TFT is NOT verified.'
fi
/usr/bin/python3 manage.py install
echo 'User installation complete. Existing Pwnagotchi and hardware configuration preserved.'
