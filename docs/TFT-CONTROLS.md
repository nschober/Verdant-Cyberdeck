# TFT controls and live Pwnagotchi screen

The welcome screen stays visible until **Enter Main Menu** is pressed (touch, mouse, or Enter key). It now reads **Network Security Dashboard**. This supersedes the earlier four-second automatic transition. F3 previews the welcome screen again. Footer navigation uses **Main Menu** and has no Exit button. Back appears on subpages and is omitted from the main menu. F1 returns from a native tool without stopping background Pwnagotchi.

## Pwnagotchi

The menu reads the existing service state. **OPEN** appears while it is running and displays its **actual live face/canvas**, not a status/log replacement. **START** appears while stopped and starts the existing service directly, without a confirmation page. Successful Start and Restart open the live screen. Stop displays its result. Errors appear on screen; systemd active state alone is not a guarantee of healthy radio/plugins. Main Menu leaves Pwnagotchi running. Existing capture popups overlay this screen as well.

A root-owned `bridge/sitecustomize.py` runtime canvas tap is scoped to Pwnagotchi through `/etc/systemd/system/pwnagotchi.service.d/verdant-screen.conf`. The original launch script prepends its installed source to PYTHONPATH and preserves this bridge path. The bridge observes the completed UI frame and atomically publishes `/run/verdant-cyberdeck/pwn-screen.png` (root:kali, 0640). The dashboard reads that canvas and fits it above its navigation bar. Original Pwnagotchi source, plugins, AI, captures, radio configuration, and virtualenv are not overwritten. Physical rendering remains disabled in the separate existing headless drop-in, so there is one framebuffer owner. An already-active Pwnagotchi restarts once when this bridge is first applied; inactive Pwnagotchi stays stopped. There is no capture or radio operation triggered by OPEN.

Frames older than 30 seconds show a waiting screen instead of passing stale content off as live. A one-second update rate is configured on this host. The original disabled-display web canvas limitation still exists; this bridge provides the actual TFT canvas separately without changing web credentials or exposing a new web endpoint.

## Pointer

Relative input uses 0.28 pixels per input count and preserves fractional motion. Position updates are coalesced; pointer publication and framebuffer drawing are capped at 30 Hz, while dashboard content is cached for 100 ms. Events are drained without rendering or writing a file for each individual X/Y movement. These are application changes; desktop mouse settings and display/driver configuration are untouched. Physical smoothness still needs observation on the TFT after apply.

## Password-protected pages

System/setup pages and both Pwnagotchi Configuration/Settings routes require the **existing kali login password** on each entry. Authentication uses the installed PAM `login` policy and checks account validity. The app does not set a new password, read/export password hashes, change PAM files, retain an unlock session, or log credentials. Failed/unavailable authentication denies access. Password input is masked and cleared when submitted or cancelled. An on-screen keyboard supports letters, digits, punctuation and spaces; Shift and Symbols expose additional keys. A physical keyboard is also supported. PAM work runs in a background worker so its configured failure delay does not freeze the pointer.

These gates protect pages within this application; they are not a replacement for the Kali lock screen or permissions and do not password-lock independent desktop applications, SSH, or a terminal the user can already access. Existing Configuration is a read-only credential-redacted summary.

## Apply and rollback

From SSH or a desktop terminal, after finishing important native-terminal work:

```bash
sudo /usr/bin/python3 /home/kali/verdant-cyberdeck/scripts/integrate_tft.py --apply --background-pwn --restart-terminal
```

The installer backs up changed runtime files, launcher and owned service drop-ins, reloads systemd and restarts the native launcher. The explicit terminal flag permits restarting an active native terminal if its overlay needs reloading; that ends its terminal session. The report states the actual actions. Use `--restore /var/backups/verdant-cyberdeck/<timestamp>/manifest.json` with the printed manifest to restore that apply. It refuses to overwrite subsequent file edits.

Software tests cover the runtime bridge with an isolated fake Pwnagotchi module, frame trust/expiry, navigation, state-dependent OPEN/START, direct actions, masked keyboard bounds, authentication result routing/cancellation and coalesced pointer patches. No real password has been supplied to tests. Successful PAM authentication using the owner's login and physical live-screen/pointer observation remain hardware acceptance checks after apply.
