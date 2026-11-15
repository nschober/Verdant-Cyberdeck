# Verification results

## Background capture and notifications

Clean-export verification: 49 tests total, 48 passed and one expected host-only skip. Python compilation, five shell-script syntax checks and offscreen startup passed. The desktop notifier uses a mocked Tk window-manager test; native overlays use actual Pillow rendering and fixtures. No real handshake was fabricated or captured by the tests, and physical overlay/desktop observation remains pending.

New tests cover capture-log recognition versus old counts/files, cursor duplicate suppression, atomic metadata, expiry/dismissal, untrusted-file rejection, synthetic labeling, popup click protection, desktop topmost geometry/expiry, service conflict preservation, background ownership, last-pass terminal composition, main-TOML preservation and rollback. Native/desktop screenshots are rendered previews; live capture and physical foreground-window observation still require the host apply and actual/synthetic event testing.


## Native TFT dashboard v2

Final portable suite: 38 tests, 37 passed and one expected host-local preservation skip. The startup/replay timing test verifies a four-second phase from the first prepared native frame, within the requested 3–5 seconds.

The previous splash-only host apply succeeded, with matching installed artwork/launcher hashes and mode `auto`. That did not establish that the full dashboard appeared on the screen. V2 now connects the real UI renderer and hit targets to the native supervisor. Tests include a simulated supervisor boot that checks the full 480×320 BGRX frame against the actual six-button renderer, plus terminal command newline delivery, touch/keyboard safety, FIFO validation and backup/rollback. Physical host application/observation is still required.


## TFT startup/AUTO fix

The redesigned splash renders at 480×320 and was visually reviewed. The patch dry-run recognizes the actual installed TFT chooser and identifies the current mode as manual. Seven new behavioral tests pass. The complete portable suite now contains 28 tests, with the expected host-only historical preservation test skipped on a clean export. No host apply has been performed from the restricted execution session: system-bus/device/root access remains unavailable. A normal-host apply, actual TFT observation and Pwnagotchi AUTO-state check are still required.


## Runtime source-export update

The host-local historical preservation check now detects configuration checksum drift since the original baseline. The source/configuration files were not written by this repository update, and the current redacted setting values match the user's export. The baseline is retained unchanged and the observed drift is not suppressed or described as a pass. A new local comparison records checksums for the remainder of this read-only review; it is not a replacement for the historical evidence.

The 21-test portable suite is verified separately on a clean export, where the expected host-local preservation check is skipped. Original exported-source hashes, repository-copy manifests and license bytes are checked directly. Source omission and redaction limits are documented in `pwnagotchi/SOURCE-EXPORT.md`. Runtime/physical-hardware checks remain unverified.


## Pwnagotchi file snapshot update

The updated local suite has 21 tests, including four exporter/redaction tests. All 21 pass on the original host, including the unchanged Pwnagotchi checksum check. Protected runtime and plugin paths remain inaccessible; 14 readable host-integration files are captured with TOML redaction. The exporter returns a partial-export status (exit 2) for the two inaccessible source roots, rather than claiming completeness. The initial GitHub publication passed its 17-test suite with the expected one host-only skip; the updated workflow must be checked separately.


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
