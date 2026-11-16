# Background Pwnagotchi and handshake popups

## Behavior

Pwnagotchi continues using its existing service, AUTO selection, radio settings, plugins and learned data. The native dashboard and ordinary terminal can remain foreground applications while it runs. Opening or closing the dashboard does not start Pwnagotchi. Start/Stop/Restart still operate the existing service explicitly.

The title is centered at font size 19, up from 17. Standard button text is bold at size 15, up from 14; long-label fallback text is bold at size 12, up from 11. The welcome screen now persists until Enter Main Menu. [Updated TFT controls](TFT-CONTROLS.md) cover the live Pwnagotchi screen, direct Start, reduced mouse sensitivity, and PAM-protected settings.

## Narrow host changes

The installer adds `/etc/pwnagotchi/conf.d/zzzz-verdant-background.toml` containing only `ui.display.enabled = false`. The original main TOML is not edited. The existing implementation checks this setting before opening/rendering the TFT, allowing Verdant to own the display. Its existing web-face rendering may also stop updating when the physical-display flag is disabled; this is a known limitation of the installed implementation.

The installer removes only `tft-terminal.service` from the installed Pwnagotchi unit's `Conflicts=` list, retaining ExecStart, virtualenv, requirements, ordering, mode flags and other settings. Dependencies cannot be cleared through an ordinary systemd drop-in, so the existing unit is narrowly patched and backed up. See the [systemd unit documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html).

The native supervisor excludes background Pwnagotchi from screen ownership and no longer stops it when launching the terminal. The legacy dedicated-radio `tft-recon.service` remains mutually exclusive with Pwnagotchi because both use the same configured radio. Verdant's normal Wi-Fi Recon page uses its explicit nmcli scan interface rather than starting that legacy service.

## Capture-event alerts

A new, separate `verdant-handshake-monitor.service` follows **future** journal records from `pwnagotchi.service`. It starts no radios and has no dependency that starts Pwnagotchi. It is enabled at boot so event monitoring survives closing the dashboard.

The parser recognizes the installed agent's `!!! captured new handshake ... !!!` log messages, including the installed timestamp/severity/thread prefix and its separating colon. The monitor logs a short event identifier after successful publication, without capture details. Journal cursors deduplicate repeated records. Existing files, old handshake counts and unrelated log text do not trigger notifications. This reports a capture event from Pwnagotchi; it does not independently verify a complete/crackable exchange.

The latest event is stored atomically in `/run/verdant-cyberdeck/handshake.json`, root-owned, group `kali`, mode 0640, with a 0750 parent directory. It contains only event metadata, not capture contents or keys. Popups expire after eight seconds. The last metadata file remains in volatile `/run` until another event or reboot.

- **Native TFT:** the dashboard and terminal compose the alert after their own window content. This covers managed native windows without racing a second framebuffer writer. Clicking the card on the dashboard dismisses it without activating a hidden menu button.
- **Graphical desktop:** a separate user-session client requests an always-on-top popup above ordinary desktop windows. It is nonmodal and does not force keyboard focus. Protected lock screens, a compositor's exclusive fullscreen layer, arbitrary independent framebuffer writers, and sessions without a running alert client are outside this guarantee.
- Bursts coalesce into the newest popup rather than an unbounded queue. The monitor follows new records after startup; events during monitor downtime are not replayed as new captures.

## Apply from SSH or a normal desktop terminal

Finish any important work in the native TFT terminal first. The explicit restart flag allows reloading an active native terminal so its popup hook is live immediately; that ends its interactive session. The installer refuses to terminate its own native-terminal cgroup.

```bash
sudo /usr/bin/python3 /home/kali/verdant-cyberdeck/scripts/integrate_tft.py \
  --apply --background-pwn --restart-terminal
```

The installer backs up changed files, installs the overlay/runtime code and passive monitor unit, reloads systemd, and restarts an already-active Pwnagotchi when its effective display/service settings changed. An inactive Pwnagotchi is not started automatically. Select Pwnagotchi → Start if needed. Pwnagotchi's boot enablement and existing AUTO selection are preserved.

A hidden `Verdant Handshake Alerts` user autostart entry is installed by `manage.py install-alerts` (also included in normal user installation). The root apply attempts to start that client as `kali` in a discovered existing graphical session without guessing DISPLAY or starting a display server. Otherwise it is available at the next graphical login, or through `~/.local/bin/verdant-alerts` from a normal desktop terminal. Its startup log is `/var/log/verdant-cyberdeck/desktop-alerts.log`.

The apply report identifies the actual foreground owner, monitor state and desktop-client launch result. Software/unit success is not proof that a physical popup was observed.

## Synthetic display test

After applying, this emits a distinctly labeled **TEST NOTIFICATION**, without capturing anything or changing Pwnagotchi:

```bash
sudo env PYTHONPATH=/usr/local/lib/verdant-cyberdeck \
  /usr/bin/python3 -m cyberdeck.alerts --test-alert
```

Use it while the dashboard, native terminal or a desktop window is foreground. Actual capture popups require a genuine new event from the existing Pwnagotchi service. Do not treat the synthetic preview as evidence of working capture hardware or a real handshake.

## Rollback and scope

Use `integrate_tft.py --restore` with the exact manifest reported by this apply. Rollback restores the backed-up Pwnagotchi unit, removes the owned headless override where newly created, restores the native renderer/runtime files, reloads systemd, and restores monitor enablement behavior. It refuses to overwrite later file edits. User launchers/autostart entries remain separately owned by the user installer/uninstaller.

No Pwnagotchi reinstall, source overwrite, plugin disablement, capture deletion, learned-data migration, network-interface definition, SSH setting, driver, SPI overlay, boot-firmware file, or framebuffer mode change is part of this update. Existing plugin/hardware errors are not silently repaired by display integration.

## Installed logger compatibility correction

The Pi’s actual capture records use `[timestamp] [WARNING] [Event Polling] : !!! captured new handshake: ... !!!`. The earlier parser omitted the separator colon, so it rejected valid records and never wrote shared notification state. This revision accepts that exact prefix while preserving anchored marker validation and journal-cursor deduplication. Ten actual recent records were accepted in a read-only check; none were replayed or published. Root apply is required to replace the monitor’s loaded code. Physical popup observation remains pending after apply. The existing desktop client already requests topmost stacking over ordinary windows.
