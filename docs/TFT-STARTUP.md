# TFT startup artwork and Pwnagotchi AUTO operation

## Confirmed causes

The current TFT is owned by `/opt/tft-terminal/launcher.py`, started by the existing `tft-launcher.service`. Desktop/XDG startup starts a different application on the graphical desktop. Changing Verdant's desktop splash image alone does not change that native TFT chooser.

The readable `/etc/pwnagotchi/mode` currently contains `manual`. The actual exported `/root/pwnagotchi-modern/tft/launch.sh` runs the existing Pwnagotchi executable with `--manual` for that value and without `--manual` for `auto`. Its standard `/root/.pwnagotchi-auto` flag takes precedence over a pending manual flag. AUTO operating mode is distinct from enabling the service at boot.

Framebuffer numbering changed between inspections: the current `/proc/fb` identifies ILI9488 as fb0, while an earlier inventory identified fb1. Existing name-based framebuffer selection is retained. No fixed framebuffer number, driver, overlay or boot setting is changed.

## Prepared fix

`cyberdeck/splash.py` renders original 480×320 artwork with a custom mark, typography and circuit detailing. The resulting `assets/splash.png` is used by the desktop/direct-framebuffer splash and can also be installed into the actual native TFT chooser.

`scripts/integrate_tft.py` defaults to a read-only plan. The apply command:

1. Validates the installed native chooser against the inspected implementation and compiles the patched source before writing anything.
2. Saves original contents, permissions and ownership in a root-only timestamped directory under `/var/backups/verdant-cyberdeck/`.
3. Installs the PNG under `/usr/local/share/verdant-cyberdeck/` and adds a one-second startup splash to the existing chooser. Its original service-selection function, input routing and name-based framebuffer selection are preserved.
4. Adopts an existing active/activating TFT owner on chooser restart, avoiding a menu drawn over Pwnagotchi. Splash-time input is ignored through the matching release to prevent an unintended launch.
5. Only with the explicit `--pwn-mode auto` option, sets the existing mode file to AUTO and uses the existing launcher's standard AUTO flag.
6. Restarts an already-running Pwnagotchi only when AUTO was explicitly requested. An inactive Pwnagotchi remains inactive until its next explicit launch. Restarts/starts the non-radio TFT chooser to load the artwork.

The existing TFT service's boot enablement is unchanged. No Pwnagotchi source, main TOML, plugin, learned data, network definition, display driver, SSH configuration, boot overlay, framebuffer mapping or graphical server configuration is written.

## Apply from a normal Pi terminal

This restricted execution session cannot connect to systemd, open display/input devices or acquire root privileges. The files and dry-run can be prepared here; the actual host apply must run from a normal terminal using your existing sudo authorization:

```bash
sudo /usr/bin/python3 /home/kali/verdant-cyberdeck/scripts/integrate_tft.py --apply --pwn-mode auto
```

The command prints the backup manifest, mode after apply and actual service states. It exits nonzero on a failed write or service action. If a service restart fails, consult that manifest and the service journal; do not assume the changes were rolled back automatically.

The splash is a startup screen for the native chooser. When Pwnagotchi or another native TFT application already owns the screen, the chooser adopts that owner and leaves its UI visible; the splash appears on a later chooser start with no active screen owner. The TFT chooser keeps its existing native menu; this patch does not move desktop Xterm windows onto the SPI display.

AUTO selection does not by itself verify the radio adapter, AI dependencies or runtime wireless compatibility. Those require host-side service/log checks. Opening the Verdant dashboard remains passive.

## Roll back

Use the exact manifest path printed by apply:

```bash
sudo /usr/bin/python3 /home/kali/verdant-cyberdeck/scripts/integrate_tft.py \
  --restore /var/backups/verdant-cyberdeck/REPORTED-TIMESTAMP/manifest.json
```

Rollback checks backup hashes and refuses to overwrite a later manual change. It restores the original launcher/artwork/mode state and restarts the existing service where needed. Source data and learned data are never removed.

## Validation limits

The patch was dry-run against the actual readable native launcher. Automated tests cover preserved service-selection logic, unknown-source refusal, startup image sizing/progress, atomic write/symlink handling, metadata-preserving backup/restore, inactive-service preservation and explicit active-service mode switching. Clean-export tests do not require root, display devices or radios. Physical display/touch and effective runtime AUTO behavior remain unverified until the host apply and user observation.
