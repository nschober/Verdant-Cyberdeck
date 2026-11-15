#!/bin/bash
set -euo pipefail
# Only the dedicated USB radio is managed here.
[[ -e /sys/class/net/wlan1 ]]
nmcli device set wlan1 managed no
ip link set wlan1 down
iw dev wlan1 set type monitor
ip link set wlan1 up
