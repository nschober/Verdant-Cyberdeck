# Verification results

## Repository preparation — Verdant Cyberdeck

After renaming, the user installer and all 17 local tests passed again. The original launcher remains a compatibility alias, and the preferred launcher is now `verdant-cyberdeck`. Tests use synthetic Pwnagotchi fixtures for portability. A clean export skips the host-local preservation check. GitHub Actions has been configured but has not run remotely; no CI success is claimed. The hardware limitations below still apply.

## Initial host verification

Executed on 2026-11-14 in the provided Kali ARM64 terminal sandbox.

| Check | Result |
|---|---|
| User installation via `bash install.sh` | PASS, exit 0 |
| Kali/aarch64 detection and framebuffer sysfs inventory | PASS |
| All requested Kali packages and GUI dependencies | Already installed |
| Python syntax compilation and imports | PASS |
| All five shell scripts, `bash -n` | PASS |
| Behavioral tests | 17 passed |
| 480×320 rendering, menu bounds, touch hit testing, back/home navigation | PASS offscreen |
| Large-button sizes and text wrapping | PASS offscreen |
| Splash/dashboard PNG generation | PASS |
| Passive startup and service confirmation guards | PASS automated tests |
| Wi-Fi escaping, BSSID/frequency fields, sort and scan failure handling | PASS fixtures |
| Existing service target, unknown-state reporting and credential omission | PASS |
| Launcher argument boundaries and missing dependency handling | PASS |
| Autostart enable/disable and uninstall rollback | PASS isolated temporary home |
| Live user autostart installation | Enabled; prior entry backed up |
| Application startup/error logging and offscreen clean exit | PASS |
| Pwnagotchi configuration/service checksums | Unchanged |
| Actual Pwnagotchi running state, dependency health | UNAVAILABLE: system-bus access denied |
| Wireless adapter detection and actual Wi-Fi scan | UNAVAILABLE: netlink/NetworkManager bus denied |
| Bluetooth controller detection and discovery | UNAVAILABLE: bus denied; bluetoothctl aborted without a bus |
| Actual desktop startup | UNAVAILABLE: no DISPLAY; verified existing `:0` socket inaccessible |
| Isolated Xvfb GUI test | UNAVAILABLE: sandbox prevents binding X sockets |
| Physical TFT output, touch calibration, terminal placement | UNVERIFIED: device nodes inaccessible |
| Direct framebuffer handoff and service-control authorization | UNVERIFIED; ownership guard tested |
| Pwnagotchi operation independent of dashboard | Service dependency independence inspected; live operation UNVERIFIED |

`python3 verify.py --hardware` returned exit 1 deliberately: unavailable hardware checks were not suppressed. The full per-check outputs are in `logs/test-results.json`. No physical test is counted as successful from fixtures or offscreen rendering. Pwnagotchi was never started or stopped for these checks.

The known remaining gap is host-side physical display/input validation and an explicit handoff from the existing enabled TFT launcher. Desktop autostart alone does not put an X11 window on the independently rendered SPI framebuffer. No existing hardware/startup service was changed to bypass that gap.
