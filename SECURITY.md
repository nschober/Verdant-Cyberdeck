# Security policy

## Supported scope

The current development branch is the only maintained version. There are no production-support or hardware-certification commitments. Review the known limitations before deploying on a device with operational radios or sensitive data.

## Reporting vulnerabilities

Do not publish credentials, captures, network identifiers, host logs or exploitation details in an issue. For a private repository, report privately to its owner using the existing authorized communication channel. Where GitHub's private vulnerability reporting is enabled, use the repository's Security tab. No reporting email address is claimed or invented by this project.

Provide the affected revision, relevant environment, impact and a minimal reproduction using synthetic data. Coordinate disclosure with the maintainer before public release of sensitive details.

## Trust boundaries

- Run the dashboard as the normal user. It never grants blanket root permissions.
- Desktop service actions use the existing polkit agent; framebuffer handoff requires existing systemctl authorization.
- No passwordless sudoers entries or system service units are installed by this project.
- Third-party tools and the existing Pwnagotchi service have their own privileges and behavior.
- Opening or closing the dashboard must not start radios, change monitor mode, or alter Pwnagotchi configuration.
- Text logs can contain tool output. Inspect them before sharing, even in a private repository.

Do not commit `/etc/pwnagotchi`, private keys, real configuration, learned data, packet captures, live installation manifests or unreviewed rollback archives.
