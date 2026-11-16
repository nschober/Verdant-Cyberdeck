# Battery, RF and Mayhem changes

## Idle CPU

The native supervisor now paints only when UI content, the pointer, an alert or a live screen changes. The idle input wait is 250 ms and input devices wake select immediately. While the pointer moves, display updates remain capped at 30 Hz. Unchanged menus do not reload fonts, re-encode full frames or rewrite the framebuffer. Fonts are cached. Background network/status refresh is 30 seconds, display-owner checks are 15 seconds, and hidden dashboard status polling is suspended. The native terminal skips unchanged frames and uses inotify wakeups for pointer updates; idle fallback/alert checks are 250 ms.

The offscreen three-second comparison against the installed v4 renderer measured 1.0512 CPU seconds (34.97% of one core) versus 0.0485 (1.59%) including the first paint. Full-frame encodes dropped from 57 to one. This is about a 95% CPU-time reduction in that controlled idle renderer benchmark. It is **not** a measured battery-runtime, electrical-power or physical framebuffer result. Actual post-apply service CPU should be sampled on the Pi. Pwnagotchi AI/radio load and external security scanners remain independent and unchanged.

## Text and configuration

The service-scoped Pwnagotchi canvas bridge increases stats fonts by three points: Bold 16→19, BoldSmall 14→17, Medium 16→19 and Small 14→17. Face and large heading sizes remain 64/28; the installed Pwnagotchi source/configuration is not rewritten. The canvas is fitted above native navigation as before. Physical layout acceptance remains pending host apply.

System/Configuration/Settings open directly without password prompts. This removes the application's page gate; Linux service privilege prompts and existing Pwnagotchi web credentials are separate and remain managed by their original policies. The notification footer no longer says “clears after 8 seconds”; its existing eight-second lifetime remains.

## RF tools

The main screen has RF Tools in its previously unused footer space. Its menus provide:

- Hardware inventory and device requirements.
- GQRX, GNU Radio Companion and Inspectrum.
- Universal Radio Hacker and RTL-433 protocol analysis.
- gr-gsm live monitor, scanner, decoder and Kalibrate RTL.
- HackRF RX/TX, HackRF sweep, RTL power/capture, bladeRF CLI and SoapySDR utilities.
- Mayhem/PortaPack remote screen and explicit controls.

Tools expose their normal interfaces, including RX/TX capabilities. Menus select no target, tune no frequency, transmit nothing and run no capture automatically. GUI applications use the discovered existing user desktop/HDMI session. The native TFT provides the launcher/CLI and Mayhem remote display; arbitrary desktop SDR GUIs are not falsely claimed to fit the 480×320 framebuffer.

`bash install-rf-tools.sh --check` checks the configured repository and architecture. `sudo bash install-rf-tools.sh --complete` installs available ARM64 packages and build dependencies, then runs source builds as the desktop user. The package list includes RTL-SDR, RTL-433, HackRF, GQRX, GNU Radio, Inspectrum, Kalibrate, SoapySDR and bladeRF. URH/gr-gsm were absent from this Kali ARM64 package metadata, so the complete workflow supplies:

- URH 2.10.0 in `~/.local/share/verdant-rf/urh-2.10.0`, using system Qt/numpy and isolated pip packages.
- gr-gsm at maintainer commit `7f37c7a067d041ce3e26c1387cad095ab4087793`, which declares GNU Radio 3.10 support, in a separate prefix. Existing GNU Radio is not rebuilt or replaced.

Build logs are in that user directory. One low-priority compiler job limits installation-time load. Wrappers are published only after import/help validation; existing wrappers are backed up. Tests cover launcher routing; source builds themselves require root dependencies and network access and have not been completed in the restricted execution session. User-installed RF applications always execute through the existing kali-user terminal/GUI, not the root TFT process.

## Mayhem remote screen

The owner confirmed a PortaPack with Mayhem v1.3.0; its exact model is unknown. No HackRF/PortaPack USB device or `/dev/ttyACM*` appeared during inspection.

The new native viewer uses the official USB protocol: `info`, `screenframeshort`, explicit button and touch commands. It accepts only detected Mayhem USB VID:PID `1d50:6018`, validates identification, caps response sizes/timeouts and does no serial probing until Connect/Open. Modern firmware screen dimensions 240×320 and 320×480 are supported and fitted beside touch controls. Select/arrows/rotary and direct screen taps operate the real device; DFU/reset/flash commands are not sent by the viewer. It polls at 0.5 Hz while open and releases the connection when leaving. Existing Pwnagotchi alerts still overlay the native screen.

This is a remote display/control client, not an ARM64 port or emulator of the device firmware. Firmware stays on the PortaPack. Live compatibility is unverified until a compatible updated device is connected.

Protocol sources: [official MayhemHub](https://github.com/portapack-mayhem/MayhemHub) and [Mayhem USB shell](https://github.com/portapack-mayhem/mayhem-firmware/blob/v2.4.0/firmware/application/usb_serial_shell.cpp). The client is an original implementation of that interface; third-party application source is not bundled.

## Firmware update preparation

The official latest stable release checked on 2026-11-16 is [v2.4.0](https://github.com/portapack-mayhem/mayhem-firmware/releases/tag/v2.4.0). The helper pins its 8,434,462-byte firmware archive and GitHub-published SHA-256 `62cb7f579423ae64414c70548361dd239a4afc7adbd288ae41fbbbfa14be96bd`.

```bash
python3 scripts/prepare_mayhem_update.py
python3 scripts/prepare_mayhem_update.py --download
```

It verifies the archive and extracts only `firmware/firmware_hackrf.bin`, recording its own hash and provenance. It never executes archive scripts, flashes a device or writes SD contents. Downloads stay under `~/Downloads/mayhem-v2.4.0`, outside repository/package artifacts. Download was attempted here and failed because this execution sandbox cannot resolve GitHub; it remains pending from a normal Pi terminal.

Before flashing, the actual connected board must be identified as HackRF One, and existing flash/SD contents backed up. New firmware also requires the matching official HackRF SD-card apps payload. The helper's `flashed` and `sd_card_updated` fields remain false. No firmware/SD update has been performed or claimed.
