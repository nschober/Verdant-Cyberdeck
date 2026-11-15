# Existing Pwnagotchi installation files

This directory now contains **14 files captured from the existing host** and a provenance manifest. These are inspection/reference snapshots. They are not installed by Verdant Cyberdeck, and nothing here was written back to the working Pwnagotchi installation.

| Directory | Included files |
|---|---|
| `host-snapshot/bin/` | Actual installed `pwnagotchi` executable wrapper |
| `host-snapshot/systemd/` | Existing Pwnagotchi, dedicated Bettercap, mesh-peer, TFT launcher, terminal, recon and console service definitions |
| `host-snapshot/tft/` | Actual existing `launcher.py`, `terminal.py` and `tft_view.py` from `/opt/tft-terminal` |
| `host-snapshot/configuration/` | Redacted existing `config.toml` and `default.toml`, plus existing mode value |
| `snapshot-manifest.json` | Original paths, snapshot hashes, redaction flags and explicitly unavailable locations |

Files other than the two `.redacted.toml` snapshots retain their captured bytes. The snapshot manifest hashes describe the repository copies, not the unredacted private configuration. The TOML snapshots preserve setting names and nonsensitive booleans/numbers; only explicitly allowed interface/language/display strings remain. Other strings and sensitive fields are replaced with `[REDACTED]`. They are **not deployable or restoration configurations**.

The scripts/service definitions can start existing radios or stop competing TFT services when run by an operator. They are stored for inspection; Verdant's installer does not activate them. Do not copy these host-specific paths to a different installation without reviewing them.

## Still missing: protected runtime source and plugins

The actual customized runtime is under `/root/pwnagotchi-modern`; the custom-plugin directory is `/usr/local/share/pwnagotchi/custom-plugins`. Both are unreadable from the current execution sandbox. **The runtime source and custom plugins are not included yet.** No public upstream checkout has been substituted for your customized files, and no empty source placeholders are supplied.

To collect them without modifying the installation, run the included read-only exporter from a normal terminal on the Pi with your existing sudo access:

```bash
cd /home/kali/verdant-cyberdeck
sudo /usr/bin/python3 scripts/snapshot_pwnagotchi.py \
  --output /home/kali/verdant-cyberdeck/backups/pwnagotchi-root-review
```

The output path must not already exist. The exporter only reads the installed files and writes a new local review directory. It never runs Pwnagotchi, systemctl, apt, network commands or an installer. Files created through sudo are assigned back to the invoking user. Existing source files, configuration, plugins, network settings, learned data and services are not changed.

The source allowlist collects code, documentation, service text and license files while excluding virtualenvs, Git internals, runtime data, learned models, captures, keys and most non-source formats. TOML is redacted. Source files themselves can still contain embedded credentials, so the collected code stays under the Git-ignored `backups/` directory until it is reviewed. Export is deliberately not an automatic GitHub upload or a complete installation backup. Its manifest lists missing and excluded files.

Once that export is available, the actual runtime/plugin source can be reviewed and added with its original licenses and notices. Missing-file status must not be replaced with a completeness claim before then.

## Licensing

The captured host-integration files are reference copies supplied from the existing installation. Existing copyright/license headers are retained. Their independent license status has not been established from an original upstream license file; the repository MIT license does not purport to relicense them. Protected third-party runtime/plugin source will need its own original licensing material when collected.
