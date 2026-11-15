# Changelog

## Unreleased — persistent native TFT dashboard

- Connect the actual six-button dashboard to the existing framebuffer/input supervisor instead of only replacing its transient splash.
- Preserve existing service handoff, F1/F2 controls and AUTO mode, and add F3 splash replay.
- Set startup/replay splash duration to four seconds, timed from the first ready native frame.
- Route interactive tools through the existing kali-user terminal with protected FIFO input.
- Install compiled root-owned runtime copies, back up every changed file, and report/log the current screen owner.
- Add native adapter and simulated-supervisor tests; keep physical observation and existing Pwnagotchi plugin errors explicitly unverified.


## Unreleased — native TFT splash and explicit AUTO mode

- Replace the plain splash with original Verdant branding, circuit artwork and readable category labels.
- Add a targeted, dry-run-first patch for the existing native TFT chooser, including active-owner adoption and splash-input suppression.
- Add verified backups/rollback and explicit AUTO-mode selection using the existing Pwnagotchi launcher mechanism.
- Preserve boot enablement, drivers, original chooser service selection and inactive Pwnagotchi state.
- Add seven behavioral tests; physical application requires a normal host terminal.


## Unreleased — exported Pwnagotchi runtime source

- Include 423 reviewed files from the existing customized runtime, including core Python, 25 built-in plugin files, custom TFT integration and original GPL/LGPL notices.
- Redact caplet credentials and host security details; retain original source/license bytes elsewhere.
- Keep the original export and bootstrap dependency environment local, and inventory omitted assets/entry points.
- Correct the exporter to collect entry points, static assets, translations, Go/build files and packaging metadata while excluding bootstrap/IDE directories.
- Record historical configuration-checksum drift without reverting the live installation.

## Existing Pwnagotchi file snapshots

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
