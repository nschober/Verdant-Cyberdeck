# Pi installation status

Installed on 2026-11-14. The full modern Pwnagotchi engine runs on the
ILI9488 TFT through `pwnagotchi.service`, enabled at boot. Bettercap is managed
by `pwnagotchi-bettercap.service`. Its dedicated adapter is wlan1; wlan0 stays
under NetworkManager for normal connectivity. The hostname is preserved.

Standard deauthentication, association and mesh advertising features are enabled
in /etc/pwnagotchi/config.toml. The selected operating mode is MANUAL, stored
in /etc/pwnagotchi/mode. Manual mode shows session results and does not run the
automatic testing/AI loop. Switch modes with the standard Web UI restart button;
the selection persists across service restarts and boots. The host launcher now
honors the mode markers written by the Web UI. Automatic mode uses the normal
upstream Wi-Fi features and saved AI model.

Pwngrid 1.11.6 is installed from the upstream aarch64 release, verified against
the release asset SHA256 digest. Source and digest are recorded in
downloads/pwngrid-source.json. pwngrid-peer.service starts with Pwnagotchi,
provides the local mesh API on 127.0.0.1:8666 and uses wlan1. Mesh advertising and peer reception are enabled in the peer daemon.
The upstream daemon skips mesh initialization when advertise=false; enabling
its standard mesh startup also fixes the otherwise broken peer-memory API.
Grid integration is enabled; network reporting to the external grid remains an
optional setting (main.plugins.grid.report = false). External inbox/account
availability and encounters with another physical peer have not been verified.

Optional plugins remain available through the Web UI and CLI. Plugins needing
[REDACTED: host-specific credentials or identity details]
specific devices/accounts to be configured. The fix_services plugin stays off
because it resets wlan0mon rather than the USB radio; auto-update stays off
because its image-level updater does not preserve this custom host runtime.
The LED plugin expects /sys/class/leds/led0, which this host does not expose.

Runtime uses Python 3.11, Torch 2.5.1, torchvision 0.20.1 and SB3 A2C MlpPolicy.
Torch 2.15 installed successfully but crashed with an illegal instruction in
A2C initialization on Cortex-A72. Dependencies are pinned accordingly and
python-prctl is included. See installed-requirements.txt for the environment.

Persistent brain and session data: /var/lib/pwnagotchi and
/var/tmp/pwnagotchi/sessions. Logs: /etc/pwnagotchi/log/pwnagotchi.log.
Identity keys: /etc/pwnagotchi/id_rsa and id_rsa.pub (generated locally with
PyCryptodome; private key mode 0600). Configuration: /etc/pwnagotchi/config.toml.
Service, mode launcher, radio lifecycle, caplet and initial configuration sources are in this
folder. config.toml is the initial template, not the live configuration.

[REDACTED: host-specific credentials or identity details]
changeme / changeme). It binds only to loopback. Bettercap also binds to
loopback, port 8081. Access remotely through an SSH tunnel if required.

Control:

```bash
systemctl restart pwnagotchi
systemctl status pwnagotchi pwnagotchi-bettercap
journalctl -u pwnagotchi -u pwnagotchi-bettercap -n 50
```

To return the TFT to its terminal and release the USB radio:

```bash
systemctl disable --now pwnagotchi
systemctl enable --now tft-terminal
```

To return to Pwnagotchi:

```bash
systemctl disable --now tft-terminal
systemctl enable --now pwnagotchi
```

The TFT terminal boot service is disabled to avoid competing boot jobs.
Starting Pwnagotchi stops tft-terminal through a systemd conflict. Stopping
Pwnagotchi also stops its Bettercap instance and restores wlan1 to managed
mode. The pre-existing bettercap.service is not modified or enabled.
The installation does not reboot the host.

Validation completed: three framebuffer backend tests; synthetic Gymnasium,
training, deterministic inference and atomic save/reload checks; CLI import;
systemd unit verification; live Bettercap API and AP reception; authenticated
web UI and 480×320 PNG; hardware framebuffer mapping with rendered pixels;
live AI training and brain.nn/brain.json writes. The built-in wlan0 connection
remained connected. Restart behavior was exercised. Boot enablement was checked;
a physical reboot and optional hardware/account plugins were not exercised.

Full integration follow-up: mode switching invokes this host's service instead
of the unrelated stock Bettercap unit. Both mode-switch branches and mesh
API enable/disable paths have regression checks in test_host.py. The regular
pwnagotchi command is installed in /usr/local/bin. Local mesh API and web
mode controls were verified. Active association/deauthentication testing was not exercised
as part of installation verification.

Model durability fix: training now copies the backup atomically rather than
moving the live brain out of the way. Interrupted training therefore leaves
the previous model available. Model writes are flushed and fsynced before
atomic replacement. The smoke test checks backup preservation. The existing
brain was recovered from its .bak after discovering this upstream behavior.
