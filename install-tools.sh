#!/usr/bin/env bash
# Package installation only. Never includes Pwnagotchi or graphics configuration.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mkdir -p logs
exec > >(tee -a logs/install-tools.log) 2>&1
mode="${1:---install}"
[[ "$mode" == --check || "$mode" == --install ]] || { echo 'Use --check or --install'; exit 2; }
arch=$(dpkg --print-architecture)
echo "Repository package checks for $arch"
packages=(python3 fonts-dejavu-core python3-tk python3-pil python3-pil.imagetk python3-evdev xterm iw network-manager nmap bettercap aircrack-ng wifite kismet bluez tcpdump tshark metasploit-framework nikto gobuster sqlmap tmux htop)
missing=()
unavailable=()
for package in "${packages[@]}"; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -qx 'install ok installed'; then
        echo "$package: installed"
    elif apt-cache show "$package:$arch" 2>/dev/null | grep -Eq "^Architecture: ($arch|all)$"; then
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
        apt-get --no-remove install "${missing[@]}"
    else
        sudo apt-get --no-remove install "${missing[@]}"
    fi
fi
if ((${#unavailable[@]})); then
    echo "Unavailable packages: ${unavailable[*]}"
    exit 1
fi
