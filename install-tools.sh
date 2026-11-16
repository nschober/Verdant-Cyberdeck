#!/usr/bin/env bash
# Package installation only. Never includes Pwnagotchi or graphics configuration.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
TASK_LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/verdant-cyberdeck/logs"
mkdir -p "$TASK_LOG_DIR"
exec > >(tee -a "$TASK_LOG_DIR/install-tools.log") 2>&1
mode="${1:---install}"
[[ "$mode" == --check || "$mode" == --install ]] || { echo 'Use --check or --install'; exit 2; }
arch=$(dpkg --print-architecture)
echo "Repository package checks for $arch"
packages=(python3-tk python3-pil python3-pil.imagetk python3-evdev python3-pyte python3-venv python3-pip fonts-dejavu-core git hcxtools xterm iw network-manager nmap bettercap aircrack-ng wifite kismet bluez tcpdump tshark metasploit-framework nikto gobuster sqlmap tmux htop)
missing=()
unavailable=()
for package in "${packages[@]}"; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -qx 'install ok installed'; then
        echo "$package: installed"
    elif apt-cache show "$package:$arch" 2>/dev/null | grep -E "^Architecture: ($arch|all)$" >/dev/null; then
        echo "$package: available for $arch"
        missing+=("$package")
    else
        echo "UNAVAILABLE: $package for $arch"
        unavailable+=("$package")
    fi
done
if [[ "$mode" == --install && ${#missing[@]} -gt 0 ]]; then
    # Preview dependency changes; refuse a plan removing installed packages.
    plan=$(apt-get --simulate --no-remove install "${missing[@]}")
    echo "$plan"
    if (( EUID == 0 )); then
        apt-get --no-remove --no-install-recommends -y install "${missing[@]}"
    else
        sudo apt-get --no-remove --no-install-recommends -y install "${missing[@]}"
    fi
fi
if ((${#unavailable[@]})); then
    echo "Unavailable packages: ${unavailable[*]}"
    exit 1
fi
