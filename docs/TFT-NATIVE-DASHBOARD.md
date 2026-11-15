# Native TFT dashboard integration (v2)

## Why the previous change was insufficient

The first integration changed only a one-second startup image in the existing three-item TFT chooser. It did not connect Verdant's actual dashboard to that screen. It also preserved an already-running native screen owner, so a terminal or Pwnagotchi screen could remain visible instead of the splash.

V2 renders the actual six-button Verdant interface through the existing chooser's framebuffer/input loop. This is a persistent dashboard after the brief splash, not another desktop window. The desktop application remains usable independently.

## Apply the prepared native integration

From a normal Pi terminal:

```bash
sudo /usr/bin/python3 /home/kali/verdant-cyberdeck/scripts/integrate_tft.py --apply
```

AUTO was already selected by the earlier successful apply. This command retains that mode and does not restart Pwnagotchi for a mode change. It installs root-owned copies of Verdant's Python modules under `/usr/local/lib/verdant-cyberdeck/`, upgrades the existing native launcher, preserves original service enablement, saves rollback backups, and restarts the chooser. No driver, boot overlay, SSH or network configuration is changed.

The command reports `display_owner`. If an existing application owns the TFT, its UI remains visible. **F1 returns from that application to the new dashboard using the existing stop-current-application behavior.** In particular, F1 stops the selected native Pwnagotchi service before returning, as the original chooser did. Start it again from the Pwnagotchi menu when desired; AUTO remains selected.

**F3 previews the splash while the dashboard owns the TFT.** The same preview is available under System → Display / Splash. The splash lasts 4 seconds, then the six-button dashboard remains visible. The four-second timer starts after artwork preparation for the first dashboard frame; an already-running screen owner does not consume that first splash interval.

## Native functionality

- Touch and mouse clicks use the dashboard's actual button rectangles, including both touchscreen axes.
- Tab/Enter navigates buttons; 1–6 selects menu tiles; Escape returns Home; arrows/wheel scroll text.
- Splash-time touches/held keys cannot turn into an unintended tool launch afterward.
- Existing F1 app return and F2 keyboard/mouse desktop handoff are retained.
- Interactive tools use the existing `tft-terminal.service`, which must run as `kali`. They do not launch an invisible Xterm on HDMI and are not executed inside the root dashboard process.
- Terminal input is accepted only through the existing kali-owned FIFO; symlinks and ordinary files are rejected.
- Pwnagotchi controls operate the existing installed service, keep the confirmation screen, and hand the framebuffer to its own UI.
- UI statuses, Wi-Fi/Bluetooth controls, on-screen help and logs use the same dashboard modules as the desktop interface. Discovery remains explicit.

The root supervisor imports only the installed root-owned module copy, not a writable home-directory Python path. Source code is compiled before any host write, and existing runtime files writable by unprivileged users are rejected.

Native UI logs are at `/var/log/verdant-cyberdeck/native.log`. Ownership messages also appear in `journalctl -u tft-launcher.service`. The apply report and logs establish software state; seeing the correct image and validating real touch input still require actual device observation.

## Backups and rollback

Use the exact manifest printed by the new apply with `--restore MANIFEST`. The manifest includes the launcher, artwork and every installed runtime module. Old v1 rollback manifests are still accepted for the paths they own. Later external edits are preserved by refusing a mismatched rollback. Source, learned data and Pwnagotchi main configuration are not deleted.

## Actual Pwnagotchi status

AUTO mode is confirmed in the live mode file. The readable host journal also reports errors from the configured PiSugar plugin and `fix_services` attempts against missing `wlan0mon`. Those are existing plugin/hardware issues; this display integration does not disable plugins, rename interfaces, or claim the runtime is healthy merely because systemd starts it. They remain a separate validation issue under the user's preservation constraints.
