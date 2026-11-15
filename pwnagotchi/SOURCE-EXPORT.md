# Source export review

The user ran the read-only exporter from a host terminal with normal sudo access. It collected 915 files and reported one unavailable location.

## Disposition

- **423 source/documentation files included:** the actual customized Pwnagotchi Python tree, 25 built-in plugin source files, bundled UI hardware libraries, custom TFT/radio/service integration, requirements and original license notices.
- **14 host snapshots already included:** wrapper, seven service definitions, three TFT helpers, two redacted configuration files and mode value.
- **478 exported bootstrap/IDE files left local:** these are dependency-environment or editor artifacts, not the application source requested for publication.
- **700 non-environment files not collected by the first exporter:** these include assets, fonts, translations, auxiliary Go/module/build material and the extensionless runtime entry point. Exact paths are listed in `source-manifest.json`; they cannot be recovered from this restricted session without another host export.
- **One nonexistent custom-plugin directory:** `/usr/local/share/pwnagotchi/custom-plugins`. No contents can be claimed for an absent directory. Built-in plugins in the actual runtime were collected.

The original 915-file review bundle remains local and unchanged. The repository manifests hash the reviewed repository copies. They do not publish hashes of unredacted credentials or private configuration.

## Redactions and provenance

The first exporter redacted all TOML strings except a small runtime allowlist, including the packaging metadata in `pyproject.toml`. That metadata is therefore not suitable for building a distribution. The corrected exporter preserves `pyproject.toml` packaging metadata for subsequent review while continuing to redact configuration TOML.

Before publication, the Bettercap caplet's username/password values were replaced with `[REDACTED]`, and credential/identity context lines in `tft/HOST-STATUS.md` were redacted. The source manifest identifies each transformation. Original source/license bytes are otherwise retained. Snapshot scripts are stored without executable Git file modes; they are not used by the Verdant installer.

The original GPLv3 and nested LGPL notices are preserved. No dependency environment, tool binary, firmware image, trained model or packet capture is redistributed by this snapshot.

## Collect the remaining source/assets

The first exporter's source allowlist was too narrow and failed to exclude a `.bootstrap` environment. That exporter has now been corrected and tested for entry points, static assets, Go source, packaging metadata and bootstrap exclusions.

Run the corrected exporter from a normal Pi terminal. Use the new output path so the first review bundle is preserved:

```bash
sudo /usr/bin/python3 /home/kali/verdant-cyberdeck/scripts/snapshot_pwnagotchi.py \
  --output /home/kali/verdant-cyberdeck/backups/pwnagotchi-root-review-v2
```

A second review is still required before uploading newly collected source/assets, particularly packaging URLs, source-embedded credentials and asset/license files. The exporter does not push to GitHub. It can still return exit 2 for the nonexistent custom-plugin directory; inspect the manifest rather than treating that status alone as a failed source copy.

This repository snapshot does not replace or reconfigure the running installation. No startup, mode, display or radio changes are needed for this export.
