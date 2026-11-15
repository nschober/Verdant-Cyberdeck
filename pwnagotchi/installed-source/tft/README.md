# Modern Pwnagotchi for the ILI9488 Pi

This folder contains the fetched jayofelony/master source with:

- A 480×320 32-bit DRM framebuffer backend (`ili9488`).
- Original led, net-pos, paw-gps, and watchdog plugin source restored.
- Missing original plugin settings restored without changing other defaults.
- Modern Gymnasium reset/step API and float32 observation shape handling.
- Per-environment channel parameters instead of an accumulating class list.
- Correct assignment of loaded Stable Baselines 3 models.
- Atomic model saving without an accidentally appended .zip suffix.
- Failed AI initialization preserves the saved brain instead of deleting it.

The accepted modern AI uses A2C MlpPolicy rather than the original LSTM.
Old TensorFlow brain files are not migrated. The original checkout is intact
at /root/pwnagotchi-usb. Source remains GPL-3.0; see LICENSE.md.

Install dependencies from the host terminal:

```bash
sudo bash /root/pwnagotchi-modern/tft/install-host.sh
```

This installs build dependencies using apt, then bootstraps uv in a separate
virtual environment. uv downloads Python 3.11 and creates `.venv`. All modern
upstream Python dependencies are installed there; the upstream setup.py is
never executed, so its system-file copying and service changes do not run.
Torch and torchvision require binary wheels instead of a source build.
No system Python packages are replaced. This requires internet and disk space.
The command is repeatable and stops on an error.

The installer runs the display backend tests, synthetic AI training/save/load
test, and full CLI import check. It does not change Wi-Fi modes, start packet
capture, stop the TFT terminal, or start Pwnagotchi. Live Bettercap, USB monitor
mode, peer mesh service, optional plugin hardware/accounts, and TFT output must
still be configured and verified after these runtime tests pass. Restoring a
plugin file does not establish that its external service is still available.

Never run upstream setup.py directly: it copies image-specific system files.
No application boot service has been enabled by this preparation.

## Completed host integration

See [HOST-STATUS.md](HOST-STATUS.md) for the installed services, passive
configuration, checks, current limitations and terminal recovery commands.
The installer above installs dependencies; service integration lives in the
adjacent unit files, caplet and radio scripts.
