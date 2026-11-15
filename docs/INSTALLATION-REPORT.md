# Historical installation report

Recorded for the original Kali Cyberdeck 3.5 installation, before the Verdant Cyberdeck rename. Paths and branding below describe that initial installation. These are observations from one host, not promises of support for other installations. The old project path now remains a compatibility symlink.

# KALI CYBERDECK 3.5

A passive 480 × 320 touchscreen dashboard for the existing Kali ARM64 installation. Source and user launchers are installed. Physical-screen operation and Pwnagotchi runtime health remain **unverified** because this execution environment blocks the host system bus, input/display devices, netlink and display sockets. See `TEST-RESULTS.md` before treating this as a hardware-validated installation.

## Run and manage

```bash
~/.local/bin/kali-cyberdeck                 # In the existing graphical login session
cd ~/kali-cyberdeck-35
./run.sh --self-test                       # Offscreen UI; no wireless operations
bash autostart.sh status
bash autostart.sh disable
bash autostart.sh enable
python3 verify.py                         # Passive checks
python3 verify.py --hardware              # Explicit Wi-Fi scan and 8-second Bluetooth discovery
```

The desktop launcher and graphical-login autostart entry use the current session environment. They never guess `DISPLAY=:0`, launch an X server, change a display mode, or start Pwnagotchi. The interface fills a 480×320 desktop; on a larger desktop it opens a fixed-size window. Escape, the window close button, and EXIT close it without stopping tools or services.

## Display findings and previous implementation

The actual system is Kali rolling 2026.3 on aarch64. Tkinter 8.6 and Pillow are installed. Sysfs identifies HDMI's `vc4drmfb` at 1920×1080 and a separate `ili9488drmfb` at 480×320. Xorg's log describes HDMI modes. The existing enabled `tft-launcher.service` draws directly to the ILI9488 framebuffer and grabs inputs; it is separate from the Xfce desktop. A fullscreen desktop window is therefore not sufficient to target this TFT. No mirroring mechanism was established from the accessible evidence.

The old project is retained at `~/.local/share/kali-cyberdeck`. Its code synchronously scans on the Tk event thread, launches tools without help arguments or persistent output, opens Pwnagotchi as a new executable rather than controlling its service, and has no live dashboard status. These are confirmed implementation defects. There was no accessible traceback proving one specific historical startup failure; the display-path mismatch is a confirmed incompatibility with relying on Tk fullscreen alone.

The new app shares a Pillow renderer between desktop and optional framebuffer backends. Buttons are at least 35 pixels tall; six main buttons occupy a 2×3 grid. Text pages have large UP/DOWN controls and wrap to pixel width. Status updates run separately from scans; old results cannot replace a page after navigation. Logs rotate at 500 KB.

### Optional direct TFT mode

```bash
./run.sh --framebuffer
```

This mode is deliberately explicit. It checks the existing `tft-launcher`, `tft-terminal`, `tft-recon`, and `pwnagotchi` service states and refuses to access the framebuffer if any owner is active or unknown. It does **not** stop these services. Their current enabled startup entries are untouched. Consequently the existing TFT launcher currently prevents simultaneous Cyberdeck framebuffer use. A host-side display/input ownership handoff is still required before using this mode; it has not been tested or automatically configured.

The backend requires accessible ABS_X/ABS_Y touch events, 480×320, zero offsets, 32-bit RGB bitfields and 1920-byte stride. It reads existing display parameters, never sets them, and does not grab/remap inputs. Touch rotation/calibration and multitouch-only devices are unverified. Desktop autostart launches the desktop backend, not a competing framebuffer writer.

Interactive tool terminals use the desktop's xterm. On a standalone framebuffer with no desktop session, use HELP ON SCREEN or a separate SSH terminal; an embedded interactive shell/onscreen keyboard is not implemented. This is a current TFT limitation.

## Existing Pwnagotchi integration

The installed `/usr/local/bin/pwnagotchi` wrapper points to `/root/pwnagotchi-modern/.venv/bin/python` and its existing application. The actual unit is `/etc/systemd/system/pwnagotchi.service`:

- Working directory and PYTHONPATH: `/root/pwnagotchi-modern`.
- ExecStart: `/root/pwnagotchi-modern/tft/launch.sh`.
- Requires: `pwnagotchi-bettercap.service` and `pwngrid-peer.service`.
- Conflicts with `tft-terminal.service`.
- Bettercap dependency runs the existing radio-start/radio-stop scripts on `wlan1`.
- Configuration is `/etc/pwnagotchi/config.toml`, with existing ILI9488 display type and AI enabled. The separate mode file is reported read-only.
- The root-owned runtime scripts and virtualenv cannot be inspected as kali here. Supported operating modes and runtime dependencies cannot be certified merely from the unit description.

The submenu provides Start, Stop, Restart, Status, Logs, and read-only Configuration. Start, Stop and Restart require a confirmation tap. Desktop controls run `pkexec systemctl ACTION pwnagotchi.service` in a persistent terminal using the existing authentication agent; no sudoers or policy rules are added. Authentication failures remain visible. Status inspects all three installed units. Logs reads their journals. Configuration shows selected settings and enabled plugin names, excluding credentials. It does not offer a configuration editor.

In explicit framebuffer mode, confirmed service control first closes the dashboard and releases its framebuffer/input handles, then uses `systemctl --no-ask-password`. It requires existing authorization and reports denial to the launching terminal. This avoids rendering over Pwnagotchi when its own TFT UI starts. This handoff is unverified on hardware.

No second Pwnagotchi installation, package change, configuration write, mode change, plugin update, learned-data write, interface change, or service start/stop was performed during development. Opening or exiting Cyberdeck does not activate or stop Pwnagotchi. The existing service has no dependency on this project, so its launch remains structurally independent. Runtime independence and health require a host `systemctl status` check; neither was falsely marked operational.

Do not infer the TFT framebuffer from the existing Pwnagotchi `ui.display.device` value: the current custom launcher may override it. No correction to that installation has been attempted.

## Menus

- Wi-Fi Recon: adapter and active-connection detection, explicit scan, signal/SSID sort, SSID/BSSID/channel/frequency/signal/security/device details, refresh, scroll, and monitor capability report. Uses nmcli/iw; never disconnects or changes interface modes.
- Pwnagotchi: the controls above and a periodically refreshed state in the dashboard header. Inaccessible service state is **unknown**.
- Network: Nmap help, Bettercap help, Metasploit console.
- Wireless: Aircrack-ng, Wifite, Kismet help and adapter/capability status. No automatic capture or monitor mode.
- Bluetooth: controller/power status, explicit 8-second discovery, info for up to eight known devices, interactive bluetoothctl. Does not power on adapters automatically.
- Traffic / Web: tcpdump, TShark, Nikto, Gobuster and SQLmap help. Terminals retain exit status/output until Enter.
- System: terminal, tmux, htop, interfaces/IP, CPU/memory, display report, rotating application logs and tool status.

Tools needing targets open help or an interactive interface. Select your authorized targets in the tool itself. Missing executables and permission errors are displayed. No unattended attack workflows are included.

## Installation and preservation

`install.sh` detects Kali ARM64, reports the session and framebuffer sizes, checks packages, compiles imports, exercises offscreen startup, and creates user launchers and its own desktop entries. With an accessible DISPLAY it additionally performs a two-second graphical smoke test. Errors are retained in `logs/install.log` and `logs/install-tools.log`.

`install-tools.sh --check` checks installed packages and architecture-specific repository metadata for missing packages. `--install` installs only missing supported packages, using a no-removal apt simulation and apt's normal confirmation prompt. Every requested package and GUI dependency was already installed here; no apt installation or OS reconfiguration was needed. No pip environment is created or modified. Repository freshness for already installed packages is not asserted.

Existing project files were backed up under `backups/20261114-201435/` before modification. The installer also backs up entries it replaces and tracks exact installed contents in `logs/installed-files.json`. Repeated enable/disable preserves original rollback copies. `logs/preserved-sha256.json` records the readable Pwnagotchi configuration and service unit checksums.

```bash
bash uninstall.sh
```

Uninstall removes only unchanged managed launcher/desktop entries and restores their previous backups. It refuses to remove files edited externally. Source, logs and backups remain available for review; installed Kali tools remain installed. Restoring the old autostart entry also restores its former enabled state. No boot, driver, SPI, SSH, NetworkManager, system service, or unrelated desktop startup settings are changed.

## Files and evidence

- `cyberdeck/`: UI, subprocess backend, device checks, installed-service integration.
- `assets/dashboard.png`, `assets/splash.png`: actual offscreen renders.
- `tests/test_integration.py`: behavioral tests and isolated install/uninstall lifecycle.
- `verify.py`: repeatable verification, machine-readable `logs/test-results.json`.
- `TEST-RESULTS.md`: passed checks and unavailable physical tests.
- `logs/`: installation, application, verification and preservation evidence.
- `backups/`: original dashboard and launcher copies; no Pwnagotchi data is bundled.

The ZIP next to this directory includes the source, screenshots, documentation, logs and project backups. It does not include Pwnagotchi configuration, private keys or learned data.
