# Changelog

## Unreleased — existing Pwnagotchi file snapshots

- Include 14 accessible existing host-integration files, configuration snapshots with strict string/secret redaction, mode value and provenance manifest.
- Identify protected runtime/custom-plugin source as missing instead of claiming a full Pwnagotchi backup.
- Add a read-only local source exporter and four behavioral tests for redaction, source preservation, exclusions and symlink handling.
- Preserve original host files and keep unreviewed privileged exports out of Git.

## Repository preparation — Verdant Cyberdeck

- Rename the product from Kali Cyberdeck 3.5 to Verdant Cyberdeck.
- Retain the legacy launcher and project-path alias for the existing installation.
- Prepare a private GitHub repository with MIT licensing, attribution, authorized-use and security policies.
- Include contribution guidance, issue/PR templates, CI, screenshots, evidence and publication inventory.
- Make the unit suite portable by replacing host-service/configuration dependencies with synthetic fixtures and explicitly skipping unavailable local preservation evidence.

## Initial local implementation — 2026-11-14

- Add a 480×320 passive touch dashboard, splash and six main menus.
- Integrate the existing Pwnagotchi service without reinstalling or reconfiguring it.
- Add explicit Wi-Fi/Bluetooth discovery and installed-tool launchers.
- Add a guarded optional framebuffer backend, desktop launcher and autostart management.
- Add reversible user installation, rollback-aware uninstallation and verification scripts.
- Record 17 passing local tests and unavailable physical hardware checks. No hardware-certified release was produced.
