#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mode="${1:---check}"
[[ "$mode" == --check || "$mode" == --install || "$mode" == --complete ]] || { echo 'Usage: install-rf-tools.sh [--check|--install|--complete]' >&2; exit 2; }
packages=(rtl-sdr rtl-433 hackrf gqrx-sdr gnuradio inspectrum urh gr-gsm kalibrate-rtl soapysdr-tools bladerf soapysdr0.8-module-hackrf soapysdr0.8-module-rtlsdr soapysdr0.8-module-bladerf)
architecture=$(dpkg --print-architecture)
printf 'Architecture: %s\n' "$architecture"
available=()
for package in "${packages[@]}"; do
    candidate=$(apt-cache policy "$package" | awk '/Candidate:/ && !found {print $2;found=1}')
    if [[ -z "$candidate" || "$candidate" == '(none)' ]]; then
        printf 'UNAVAILABLE in configured repositories: %s\n' "$package"
        continue
    fi
    package_arch=$(apt-cache show "$package=$candidate" | awk '/^Architecture:/ && !found {print $2;found=1}')
    if [[ "$package_arch" != "$architecture" && "$package_arch" != all ]]; then
        printf 'UNSUPPORTED ARCHITECTURE: %s (%s)\n' "$package" "$package_arch"
        continue
    fi
    printf 'AVAILABLE: %s %s (%s)\n' "$package" "$candidate" "$package_arch"
    available+=("$package")
done
if [[ "$mode" == --install || "$mode" == --complete ]]; then
    (( EUID == 0 )) || { echo 'Installation requires host sudo.' >&2; exit 1; }
    ((${#available[@]})) || { echo 'No compatible RF packages available.' >&2; exit 1; }
    apt-get install --no-install-recommends -y "${available[@]}"
fi

if [[ "$mode" == --complete ]]; then
    apt-get install --no-install-recommends -y git cmake g++ pkg-config python3-venv python3-pip python3-dev python3-numpy python3-psutil python3-pyqt6 python3-setuptools python3-wheel cython3 gnuradio-dev gr-osmosdr libosmocore-dev libboost-all-dev pybind11-dev python3-pybind11 libgmp-dev libsndfile1-dev libhackrf-dev librtlsdr-dev libbladerf-dev python3-scipy python3-bitstring
    build_user="${SUDO_USER:-kali}"
    [[ "$build_user" != root ]] || { echo 'Set SUDO_USER to the normal desktop user for isolated builds.' >&2; exit 1; }
    runuser -u "$build_user" -- bash "$PWD/scripts/build-rf-tools.sh"
fi
