# Contributing

Start with the README, `docs/ARCHITECTURE.md`, and `TEST-RESULTS.md`. Keep the distinction between automated checks, offscreen rendering and physical hardware validation explicit.

## Development checks

On Debian/Kali, install development runtime dependencies without replacing an existing Pwnagotchi environment:

```bash
sudo apt-get install python3-tk python3-pil python3-pil.imagetk python3-evdev xterm fonts-dejavu-core
python3 -m compileall -q cyberdeck manage.py verify.py
python3 -m unittest discover -s tests -v
for script in *.sh; do bash -n "$script"; done
./run.sh --self-test
```

A fresh clone skips the host-local preservation-manifest test. That skip is expected and must not be described as a successful check of someone's Pwnagotchi installation. The remaining tests use synthetic configuration and service fixtures. `verify.py --hardware` actively requests Wi-Fi and Bluetooth discovery; never run it as routine CI.

## Changes

Explain the problem, behavior after the change, validation, and remaining limitations in a pull request. Add behavioral tests for changes to process control, parsing, privilege boundaries or safety gates. Keep subprocess arguments as arrays; do not interpolate user input into shell commands.

Do not alter display drivers, boot overlays, SSH, network definitions or third-party Pwnagotchi settings through this project. Do not add automatic radio operations to startup. Use synthetic examples and redact sensitive material before submitting evidence.

Contributions are submitted under this repository's MIT license. Submit only material you have the right to contribute and retain required third-party attribution. Disclose significant generated code and verify its behavior.
