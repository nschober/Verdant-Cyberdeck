# Existing Pwnagotchi installation files

This directory contains the **reviewed source exported from the existing installation**, alongside host snapshots and a fresh-install workflow. The snapshot alone remains inspection material. The [package installer](../docs/INSTALLABLE-PACKAGE.md) reconstructs complete pinned upstream source and overlays reviewed Python/TFT changes, retaining original entry points and assets. It refuses an existing Pwnagotchi installation.

| Location | Contents |
|---|---|
| `installed-source/` | 423 reviewed application/source/documentation files from `/root/pwnagotchi-modern`, including core Python, 25 built-in plugin files, hardware UI libraries and the custom TFT integration |
| `host-snapshot/bin/` | Original installed `pwnagotchi` executable wrapper |
| `host-snapshot/systemd/` | Seven actual Pwnagotchi/Bettercap/peer/TFT service definitions |
| `host-snapshot/tft/` | Existing TFT launcher, terminal and shared view source |
| `host-snapshot/configuration/` | Redacted existing config/default TOML and the mode value |
| `snapshot-manifest.json` | Provenance for the 14 host snapshots |
| `source-manifest.json` | Source paths, repository-copy hashes, transformations, export omissions and unavailable locations |
| `SOURCE-EXPORT.md` | Export review, limitations and the command to collect remaining assets/entry points |

## What was preserved

The reviewed source is taken from the user's existing custom installation, not substituted with an upstream clone. Original copyright notices and license text remain intact. Source files retain captured bytes except the declared configuration/credential redactions in the manifest. The original local export remains untouched under `backups/pwnagotchi-root-review/`.

Configuration snapshots retain setting names, booleans/numbers and a small allowlist of interface/language/display strings. Other strings and sensitive values are redacted. The captured Bettercap caplet also has its API username/password removed, and credential/identity context in the host-status document is redacted. These copies are **not deployment or restoration configurations**.

No installed source, configuration, service, network setting, key, learned data or plugin was changed to produce the repository snapshot. No captured installer, driver helper, service definition or radio script was run. Such scripts can change networking or display ownership if an operator explicitly executes them; Verdant does not activate the snapshot.

## Limits of this capture

The source exporter omitted the executable entry point, static assets, translations, fonts and some auxiliary Go/build files in its first version. Those omissions are listed in `source-manifest.json`. The captured `pyproject.toml` and configuration TOML are redacted, so this snapshot is not a complete runnable/buildable distribution. See `SOURCE-EXPORT.md` for the corrected exporter and a second, non-overwriting export command.

The custom-plugin path `/usr/local/share/pwnagotchi/custom-plugins` does not exist on the exported host. This is the export's one unavailable location; it is not a claim that custom plugins were successfully copied. The 25 built-in plugin source files under the runtime are included.

Bootstrap/virtualenv packages, IDE state, keys, captures, learned data and unreviewed secrets are not uploaded. A source snapshot is not a complete device backup.

## Original licensing

The runtime's original **GNU GPL version 3** text is preserved at [`installed-source/LICENSE.md`](installed-source/LICENSE.md). The bundled DFRobot library's **LGPL version 2.1** notice remains at [`installed-source/pwnagotchi/ui/hw/libs/dfrobot/LICENSE`](installed-source/pwnagotchi/ui/hw/libs/dfrobot/LICENSE). The auxiliary peer-source directory retains its own original GPL text and other notices. Retained headers and notices must be reviewed for the corresponding files.

**Verdant's root MIT license does not relicense this supplied Pwnagotchi source or its bundled libraries.** The separate host-integration snapshots retain any original headers; their independent upstream licensing has not been established beyond the provenance supplied by this installation.

## Fresh-install components

- `../scripts/materialize_pwnagotchi.py`: clones verified upstream commit `6cdc89226478fd42d7bcca6a9faa05d9f3280701` and applies a hashed Python/TFT overlay; it never copies redacted configuration snapshots.
- `installer/requirements-pi400.txt`: direct dependency pins from the working Python 3.11 / Torch 2.5.1 Pi runtime.
- `../scripts/install_pwnagotchi_fresh.py`: an explicit fresh-host-only installer that generates private configuration, installs the isolated runtime and matching dependencies, and leaves Pwnagotchi services stopped/disabled.
- `../install.sh --complete --fresh-pwn --interface wlan1`: complete fresh-host profile after confirming the dedicated interface and existing working ILI9488 driver. This flag is refused on the existing Pi.

See the package guide for limitations, licensing and rollback. A fresh installation was not performed on the working Pi.
