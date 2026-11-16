# Automatic daily Hashcat preparation and spreadsheet

Verdant processes local captures from the **existing Pwnagotchi configuration**. On this Pi that directory is `/var/lib/pwnagotchi/handshakes`. It uses the already-installed `/usr/bin/hcxpcapngtool` from `hcxtools` (installed ARM64 package: 7.1.2-1). No Pwnagotchi files, raw captures, plugins, radio settings, or network configuration are changed.

## Output

- `/var/lib/verdant-cyberdeck/hashcat/YYYY-MM-DD.22000`: one deduplicated mode-22000 file per day, combining usable PMKID/EAPOL records from every processed capture for that day.
- `/var/lib/verdant-cyberdeck/hashcat/handshakes.csv`: Excel/LibreOffice-compatible spreadsheet, UTF-8 with BOM and quoted columns. Each capture/record observation has a row. Failed conversions and captures with no usable record also have a status row.
- `.processor-state.json`: private checkpoint and ledger history; do not delete it if you want to retain processing history.

Dates use each capture file's modification time in the Pi's local timezone, including its historical UTC offset. They are **saved-file dates**, not an independently decoded over-the-air acquisition timestamp. Existing captures are backfilled into their saved dates on first start. A capture processed after midnight still goes into its saved date. There is no new daily file until a usable record exists for that day.

### Spreadsheet columns

| Column | Meaning |
| --- | --- |
| capture_date | Saved capture's local date; daily grouping key |
| captured_at | Source file modification timestamp with UTC offset |
| timezone | Local timezone label at that saved time |
| source_capture | Capture path relative to configured capture directory |
| capture_sha256 | SHA-256 of the unchanged snapshot processed |
| capture_size_bytes | Original capture size |
| capture_format | pcap, pcapng, or cap filename extension |
| ssid | Decoded SSID, with nonprintable characters escaped |
| ssid_hex | Exact SSID bytes from the converted record |
| access_point_mac | Access point BSSID |
| client_mac | Station/client MAC |
| handshake_type | EAPOL or PMKID, as emitted by hcxtools |
| record_sha256 | Stable identifier for the complete converted hash record |
| message_pair_hex | Original EAPOL message-pair flags; empty for PMKID |
| daily_hash_file | Combined daily `.22000` file path |
| converted_at | Conversion attempt timestamp with UTC offset |
| status | converted, no_usable_hash, or error |
| records_in_capture | Distinct usable records emitted for this capture |
| new_daily_records | Records this conversion newly added to the daily set |
| converter | Converter executable name |
| processing_seconds | Conversion attempt duration |
| error | Bounded diagnostic text on failure |

CSV cells that could be interpreted as formulas are escaped. SSIDs and filenames are untrusted data. A repeated hash from separate captures can have multiple source-observation rows in the ledger while appearing only once in that day's hash file. Replacements/updates of a source file retain prior conversion rows. Per-capture record counts repeat across that capture's rows and should not be summed without grouping by capture/version.

Channel, frequency, RSSI, vendor, and plaintext passwords are not supplied by the `.22000` records and are not invented. The original captures are retained for further analysis. `converted` means hcxtools emitted a structurally valid record; it does not prove a complete/crackable exchange or reveal a password.

## Processing behavior

A passive independent service polls every five seconds, requires the file to remain unchanged across two scans and be at least ten seconds old, and converts a private snapshot. It verifies the original still matches before publishing. A still-growing file is deferred; a later source change is processed again. Nested capture directories are included without following symlinks. Output is written atomically, with one processor lock and persistent checkpoints. Duplicate records are removed within each daily output. Failures are recorded and retried after at least 60 seconds; unchanged captures with no usable hash wait until their source changes. Captures above 256 MiB and daily files above 128 MiB report explicit errors rather than consuming unbounded memory. Each converter invocation has a 120-second timeout.

The service does not start Pwnagotchi, open wireless interfaces, disconnect networking, run Hashcat, select a wordlist, make password guesses, or contact a remote service. It only prepares offline files. Its systemd sandbox has a private network namespace, read-only capture access and write access to its own output directory. The dashboard does not need to be open.

Daily hashes and CSV are root-owned with group `kali`, mode 0640, in a 0750 directory. The checkpoint and lock use 0600. Treat all generated material as sensitive audit data. No generated hashes, ledger, raw captures, or checkpoint are committed to the repository or ZIP.

## Install on this Pi

The dependency already exists; no additional package installation is needed on this host. Inspect the read-only plan:

```bash
python3 scripts/install_handshake_processor.py
```

From SSH or a normal desktop terminal, install/start the passive processor and enable it at boot:

```bash
sudo /usr/bin/python3 /home/kali/verdant-cyberdeck/scripts/install_handshake_processor.py --apply
```

The installer reads the effective source directory from defaults, main TOML and sorted existing drop-ins, backs up its own runtime module and unit, and writes no Pwnagotchi configuration. Existing sources are backfilled automatically. `verdant-handshake-processor.service` has no dependency that activates Pwnagotchi. Its root-owned code lives in the existing Verdant runtime.

Check progress:

```bash
systemctl status verdant-handshake-processor.service --no-pager
journalctl -u verdant-handshake-processor.service -n 30 --no-pager
ls -l /var/lib/verdant-cyberdeck/hashcat/
```

## Stop or rollback

```bash
sudo systemctl disable --now verdant-handshake-processor.service
```

For a verified rollback of installed code/unit, use the exact backup manifest printed by install:

```bash
sudo /usr/bin/python3 /home/kali/verdant-cyberdeck/scripts/install_handshake_processor.py --restore /var/backups/verdant-cyberdeck/processor-TIMESTAMP/manifest.json
```

Rollback restores prior service enablement/running behavior and code; it retains captures, daily hash files, CSV, and checkpoint. The regular dashboard uninstaller does not delete this sensitive output or this independently installed processor; stop/rollback it separately.

## Validation

Behavioral tests cover daily aggregation, deduplication, date separation, CSV metadata and formula escaping, stable-file deferral, modified-source history, checkpoint recovery, nested input and symlink refusal, conversion failures/no usable hash, mode-22000 parsing, singleton locking and network-independent service settings. The actual installed hcxpcapngtool was tested with a synthetic empty PCAP and did not create a false hash. Tests use synthetic hash records; no passwords were attacked and no radio/capture operation was triggered. Automatic processing of the real root-owned capture directory requires the host apply and remains pending until that service is installed.
