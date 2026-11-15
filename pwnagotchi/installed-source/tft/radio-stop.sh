#!/bin/bash
set -u
if [[ -e /sys/class/net/wlan1 ]]; then
    ip link set wlan1 down
    iw dev wlan1 set type managed
    ip link set wlan1 up
    nmcli device set wlan1 managed yes
fi
