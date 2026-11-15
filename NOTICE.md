# Attribution and scope

Verdant Cyberdeck was originally developed as **Kali Cyberdeck 3.5**. Its initial implementation was generated with OpenAI Codex and tested in a restricted terminal environment on a Kali ARM64 host. The maintainer must review changes before deploying them on hardware.

The MIT license in this repository covers the project's own source and documentation to the extent the contributors hold applicable rights. It does not relicense third-party software, vendor names, logos, protocols or hardware designs. No third-party tool binaries, complete Pwnagotchi runtime distribution, OS image, driver, firmware, pretrained model or private dataset is included. The `pwnagotchi/host-snapshot/` directory contains supplied host-integration reference files and redacted configuration; those copies retain their original headers and are not relicensed by the repository MIT license. Original upstream licensing for these custom host helpers has not been verified. See `pwnagotchi/README.md` for the exact scope.

Runtime dependencies and external tools include Python/Tkinter, Pillow, evdev, Xterm, NetworkManager, iw, BlueZ, Nmap, Bettercap, Aircrack-ng, Wifite, Kismet, tcpdump, Wireshark/TShark, Metasploit Framework, Nikto, Gobuster, SQLmap, tmux and htop. Pwnagotchi integration controls an existing local installation. Each external project remains subject to its own license and distribution terms; review those terms before redistributing packages or building an appliance image.

Kali Linux, Raspberry Pi, GitHub, OpenAI, Pwnagotchi, and the other product names belong to their respective owners. References identify compatibility targets and integrations. This independent project claims no endorsement or affiliation with those projects or vendors. No Kali dragon or third-party logo is bundled.

The historical application under `docs/legacy/` is retained as development evidence from the supplied project. It is not an installer, a supported entry point, or a separate third-party distribution. Generated screenshots depict this project's own interface.

The license text follows the [Open Source Initiative MIT template](https://opensource.org/license/mit). Licensing and authorized-use documentation cannot guarantee that a particular deployment or testing engagement complies with every jurisdiction or agreement.
