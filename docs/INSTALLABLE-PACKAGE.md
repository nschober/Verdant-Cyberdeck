# Installable distribution

The complete repository is distributed as source, a Debian package, and a Python application wheel. The full **Debian/source distributions** include installers, existing-install integrations, reviewed Pwnagotchi source/overlay, upstream pins, RF builds, tests, documentation and license notices. The wheel installs the dashboard application; system services and full tool installation use the source or Debian setup workflow.

This is a network-assisted installer, not a fully offline OS image. Kali packages, Python 3.11/runtime wheels, missing RF sources and verified firmware/peer artifacts are fetched from their declared upstreams as needed. Display drivers, boot settings, SSH, desktop environments and network definitions are not installed or rewritten.

## Existing Pi: one setup entry point

Inspect without modifying anything:

```bash
bash install.sh --check
```

Install the complete profile from a normal Pi terminal (SSH/HDMI, outside a native terminal that may need restarting):

```bash
sudo bash install.sh --complete
```

This refreshes repository metadata, installs declared dependencies, installs the user's launchers/autostart, validates offscreen startup, integrates a detected existing compatible TFT/Pwnagotchi, installs the independent daily converter/CSV service, and installs RF packages plus isolated URH/gr-gsm builds. Existing Pwnagotchi source/configuration, mode, plugins, credentials and learned data are preserved. An already-active Pwnagotchi reloads the requested live-screen/font bridge if it changed; stopped Pwnagotchi is not started. The native terminal may restart to load its battery redraw changes. Root stages run with sudo; source RF builds run as the invoking desktop user with one low-priority build job.

Install reports are stored in `~/.local/state/verdant-cyberdeck/installation-report.json`. If any stage fails, setup stops with visible errors and the report identifies completed stages. Missing tools are not silently claimed installed. The source checkout should remain available for diagnostics and its backup manifests.

## Fresh host Pwnagotchi, with original source and TFT changes

The supported target is Kali ARM64 on the Pi 400 with the default `kali` account and an already-working ILI9488 framebuffer. A fresh install needs an explicitly selected dedicated wireless interface:

```bash
sudo bash install.sh --complete --fresh-pwn --interface wlan1
```

**The fresh option refuses an existing Pwnagotchi before installing anything.** It is not an upgrade or replacement path for this user's Pi.

The workflow creates missing native prerequisites in a stopped state, clones `jayofelony/pwnagotchi` at verified commit `6cdc89226478fd42d7bcca6a9faa05d9f3280701`, and overlays the reviewed existing Python/TFT modifications. It retains upstream entry points, defaults, web assets, fonts and translations that were missing from the old inspection-only export. Redacted TOML/pyproject snapshots are never installed. It uses a separate Python 3.11 runtime and the working Pi's direct dependency pins, including Cortex-A72-compatible Torch 2.5.1/torchvision 0.20.1. Upstream's image/system-file setup.py installer is not run.

Configuration is generated afresh with a selected interface, loopback web/API bindings and random credentials stored only in root-readable files. It writes the matching Bettercap/peer units, verifies the pinned ARM64 pwngrid 1.11.6 archive digest, and leaves Pwnagotchi services stopped and disabled. MANUAL is the initial fresh mode. Wireless activity is not started by installation or dashboard opening. The normal upstream feature settings remain available for explicit operation/configuration. The dedicated adapter's start script refuses to disconnect an already-connected NetworkManager interface.

The existing source snapshot still has historical/redacted omissions; the **materializer** restores complete original upstream assets rather than pretending the snapshot alone is a runnable installer. The resulting source carries `VERDANT-SOURCE.json` with every applied overlay file/hash. Original GPLv3 and nested library notices remain intact. Verdant's MIT license does not relicense Pwnagotchi.

Fresh installation requires a live package/network environment and is not end-to-end hardware tested on this working Pi: reinstalling it would violate the preservation requirement. The script refuses partial/unrecognized existing destinations and leaves failed fresh attempts for inspection rather than deleting them automatically.

## Debian and Python artifacts

Build without installing:

```bash
python3 scripts/build_python.py
python3 scripts/build_deb.py
```

Outputs in `dist/`:

- `verdant_cyberdeck-0.5.0-py3-none-any.whl`: Python dashboard application.
- `verdant_cyberdeck-0.5.0.tar.gz`: complete source distribution including setup workflows.
- `verdant-cyberdeck_0.5.0_all.deb`: full repository under `/opt/verdant-cyberdeck`, CLI launchers, desktop entry and declared dependencies.

Install the Debian artifact with repository dependency resolution:

```bash
sudo apt install ./dist/verdant-cyberdeck_0.5.0_all.deb
sudo verdant-setup --complete
```

Package installation itself has no post-install service/radio/firmware activation hook. The explicit setup command performs integration. The dashboard's logs/previews use writable per-user state/cache paths when installed under read-only `/opt` or site-packages. The wheel does not install systemd services automatically.

CI builds and uploads the distribution artifacts. Generated captures, hashes, CSV ledgers, private keys, credentials, learned data, installation logs, local backups and firmware downloads are excluded from distribution.

## RF, Mayhem and battery changes

See [battery/RF/Mayhem integration](BATTERY-RF-MAYHEM.md). Receive and transmit-capable tools are included through their normal explicit interfaces. URH is installed in an isolated venv; gr-gsm uses a pinned GNU Radio 3.10-compatible upstream source in a separate user prefix. No existing GNU Radio or Pwnagotchi virtualenv is replaced.

Firmware remains a device-specific operation. A verified Mayhem archive preparer is included, but it never flashes a device or writes an SD card implicitly. The PortaPack was not connected during development; its reported firmware is v1.3.0 and needs an update before modern USB remote-screen operation can be verified.

## Removal and rollback

`bash uninstall.sh` removes/restores only the user's managed dashboard launchers/autostart entries. Debian removal uninstalls package-owned `/opt`/launcher files. Independently applied native/service changes have their own printed verified rollback manifests; restore those before deleting their integration script. The handshake processor has its own stop/rollback workflow. Existing/fresh Pwnagotchi, downloaded tool environments, captures, CSV/hash outputs, learned data, display drivers and networking are retained. No uninstaller erases firmware or resets hardware.
