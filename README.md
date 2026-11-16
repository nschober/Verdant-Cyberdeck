# Verdant Cyberdeck

A 480 × 320 touchscreen dashboard for the Raspberry Pi 400 running Kali Linux ARM64. Opening the dashboard starts no wireless operations.

![Verdant Cyberdeck dashboard](assets/dashboard.png)

## Install

Download or clone this private repository and extract it to a directory you plan to keep. In that directory, run the installer as your normal desktop user.

```bash
bash install.sh
~/.local/bin/verdant-cyberdeck
```

The installer requests sudo for missing runtime dependencies, runs its offscreen startup check, and creates user launchers and graphical login entries. The launcher uses the extracted directory, so reinstall from the new location if you move it. Installation logs are saved in `logs/install.log`.

Kali ARM64 and an existing graphical session are required for the desktop interface. The ILI9488 display driver and the optional Pwnagotchi installation are managed on the host. The installer leaves their configuration in place.

## Run and maintain

| Task | Command |
| --- | --- |
| Launch the dashboard from the project directory | `bash run.sh` |
| Verify startup offscreen | `bash run.sh --self-test` |
| Start direct TFT mode | `bash run.sh --framebuffer` |
| Check optional tools | `bash install-tools.sh --check` |
| Disable dashboard login startup | `bash autostart.sh disable` |
| Remove managed user entries | `bash uninstall.sh` |

Direct TFT mode needs a compatible free framebuffer and input-device access. Display ownership checks can block it while an existing TFT service holds the display. Uninstall retains source, installed packages, logs, and backups.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [TFT controls](docs/TFT-CONTROLS.md)
- [Native TFT integration](docs/TFT-NATIVE-DASHBOARD.md) and [background alerts](docs/BACKGROUND-ALERTS.md)
- [Offline capture inventory](docs/HANDSHAKE-PROCESSING.md) and [Pwnagotchi source snapshot](pwnagotchi/README.md)
- [Verification results](TEST-RESULTS.md) and [release inventory](docs/PUBLICATION.md)
- [License](LICENSE) and [third-party notices](NOTICE.md)

Physical TFT and touch behavior require verification on the target Pi.
