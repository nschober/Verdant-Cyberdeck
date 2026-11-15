# Architecture

`run.sh` invokes `cyberdeck.main`. A shared Pillow renderer provides the exact 480×320 image used by both backends. `Dashboard` owns menu state, touch hit boxes, confirmation screens, text wrapping and background jobs. Generation tokens prevent results from an old page from replacing a new page.

| Component | Responsibility |
|---|---|
| `main.py` | Logging, argument parsing, inherited desktop session, offscreen checks |
| `dashboard.py` | Splash, six main menus, footer controls, background result queue |
| `framebuffer.py` | Explicit direct TFT access with ownership and pixel-format guards |
| `backend.py` | Bounded subprocess calls and executable detection |
| `pwnagotchi.py` | Existing unit status/control arguments, read-only selected config and journal |
| `wifi_recon.py` | nmcli parsing, explicit scans, sorting, iw capabilities |
| `bluetooth.py` | BlueZ controller/device status and explicit discovery |
| `launchers.py` | Help/interactive tool terminals and desktop authorization |
| `system_status.py` | Network, memory, CPU and framebuffer diagnostics |
| `manage.py` | Exact-content ownership manifest, backups and rollback |
| `verify.py` | Repeatable software checks and explicit optional hardware checks |

The desktop backend inherits DISPLAY from the login session. It never guesses an X socket. The framebuffer backend never starts a display server or changes modes. It refuses unknown or active ownership by the existing TFT/Pwnagotchi services.

Pwnagotchi remains an external installation. The dashboard controls the discovered host's existing `pwnagotchi.service`, not a second executable process. Its current related service names and custom installation paths reflect one host; this implementation is not a universal Pwnagotchi installer or compatibility detector.

The installer writes user launcher/desktop files and tracks their exact contents. Runtime manifests and backups are host-local and are not portable deployment artifacts. Restoring those manifests on a different host is unsupported.
