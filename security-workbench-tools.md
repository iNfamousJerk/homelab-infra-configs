# Security Workbench — Upstream Tool Tracking

> Reference for the security-testing distribution (Parrot Security) tools installed on a dedicated workbench container. Use this to follow each upstream project on GitHub to monitor releases and security patches.

## Stay patched (3 layers)

1. **Distro packages (easiest)** — covers most tools. Weekly: `sudo apt update && sudo apt upgrade -y`.
2. **GitHub "Watch → Releases"** on the tools you use most — GitHub notifies you of new releases and security advisories.
3. **Manual/standalone tools** (Burp Suite, some Python tools) update via their own mechanism.

## Core suite

| Tool | What it's for | Upstream GitHub |
|------|--------------|-----------------|
| **nmap** | Network discovery & port scanning — the #1 recon tool | [nmap/nmap](https://github.com/nmap/nmap) |
| **masscan** | Ultra-fast internet-wide port scanner | [robertdavidgraham/masscan](https://github.com/robertdavidgraham/masscan) |
| **Metasploit** (`msfconsole`) | Exploit development & execution framework | [rapid7/metasploit-framework](https://github.com/rapid7/metasploit-framework) |
| **Burp Suite** | Web app security testing — intercept HTTP(S) traffic | [PortSwigger](https://github.com/PortSwigger) |
| **Wireshark/tshark** | Network packet capture & analysis | [wireshark/wireshark](https://github.com/wireshark/wireshark) |

## Password & hash cracking

| Tool | What it's for | Upstream GitHub |
|------|--------------|-----------------|
| **hashcat** | Fastest password/hash cracker (GPU) | [hashcat/hashcat](https://github.com/hashcat/hashcat) |
| **John the Ripper** | Offline password cracker (CPU) | [openwall/john](https://github.com/openwall/john) |
| **hydra** | Online password brute-forcing | [vanhauser-thc/thc-hydra](https://github.com/vanhauser-thc/thc-hydra) |
| **medusa** | Parallel network login brute-forcer | [jmk-foofus/medusa](https://github.com/jmk-foofus/medusa) |
| **cewl** | Generate custom wordlists from website content | [digininja/CeWL](https://github.com/digininja/CeWL) |

## Web application testing

| Tool | What it's for | Upstream GitHub |
|------|--------------|-----------------|
| **sqlmap** | Automated SQL injection detection & exploitation | [sqlmapproject/sqlmap](https://github.com/sqlmapproject/sqlmap) |
| **nikto** | Web server scanner | [sullo/nikto](https://github.com/sullo/nikto) |
| **gobuster** | Directory/file/DNS brute-forcing (Go) | [OJ/gobuster](https://github.com/OJ/gobuster) |
| **ffuf** | Fast web fuzzer | [ffuf/ffuf](https://github.com/ffuf/ffuf) |
| **dirb** | Classic directory brute-forcer | [v0re/dirb](https://github.com/v0re/dirb) |
| **dirsearch** | Web path scanner (Python) | [maurosoria/dirsearch](https://github.com/maurosoria/dirsearch) |
| **commix** | Automated command injection testing | [commixproject/commix](https://github.com/commixproject/commix) |

## Active directory & network authentication

| Tool | What it's for | Upstream GitHub |
|------|--------------|-----------------|
| **NetExec** (`netexec`) | AD / SMB / WinRM exploitation toolkit | [Pennyw0rth/NetExec](https://github.com/Pennyw0rth/NetExec) |
| **Evil-WinRM** | WinRM shell for Windows hosts | [Hackplayers/evil-winrm](https://github.com/Hackplayers/evil-winrm) |
| **impacket** | Python AD/SMB/WinRM protocol attack toolkit | [fortra/impacket](https://github.com/fortra/impacket) |
| **smbclient** | SMB/CIFS file share access | [samba-team/samba](https://github.com/samba-team/samba) |
| **enum4linux** | Windows/Samba enumeration | [CiscoCXSecurity/enum4linux](https://github.com/CiscoCXSecurity/enum4linux) |
| **ldapsearch** | LDAP directory querying | [openldap/openldap](https://github.com/openldap/openldap) |

## Network analysis & MITM

| Tool | What it's for | Upstream GitHub |
|------|--------------|-----------------|
| **tcpdump** | Command-line packet capture | [the-tcpdump-group/tcpdump](https://github.com/the-tcpdump-group/tcpdump) |
| **netcat** | Read/write network connections | [dievilz/Netcat](https://github.com/dievilz/Netcat) |
| **bettercap** | MITM / network reconnaissance & attack framework | [bettercap/bettercap](https://github.com/bettercap/bettercap) |
| **aircrack-ng** | WiFi auditing — capture & crack WPA/WEP | [aircrack-ng/aircrack-ng](https://github.com/aircrack-ng/aircrack-ng) |
| **onesixtyone** | Fast SNMP community-string brute-forcer | [trailofbits/onesixtyone](https://github.com/trailofbits/onesixtyone) |

## Recon & OSINT

| Tool | What it's for | Upstream GitHub |
|------|--------------|-----------------|
| **Maltego** | GUI OSINT/data-mining graph tool | [paterva/Maltego](https://github.com/paterva/Maltego) |
| **dnsrecon** | DNS enumeration | [darkoperator/dnsrecon](https://github.com/darkoperator/dnsrecon) |
| **dnsenum** | Multithreaded DNS brute-forcing | [fwaeytens/dnsenum](https://github.com/fwaeytens/dnsenum) |

## Forensics & reverse engineering

| Tool | What it's for | Upstream GitHub |
|------|--------------|-----------------|
| **binwalk** | Firmware & binary file analysis | [ReFirmLabs/binwalk](https://github.com/ReFirmLabs/binwalk) |
| **foremost** | Recover deleted files / carve by type | [korczis/foremost](https://github.com/korczis/foremost) |
| **gdb** | Debugger for reverse engineering | [bminor/binutils-gdb](https://github.com/bminor/binutils-gdb) |

## Python security libraries

| Library | What it's for | Upstream GitHub |
|---------|--------------|-----------------|
| **impacket** | AD/protocol attack primitives | [fortra/impacket](https://github.com/fortra/impacket) |
| **pwntools** | CTF/exploit-development framework | [Gallopsled/pwntools](https://github.com/Gallopsled/pwntools) |
| **scapy** | Packet crafting & manipulation | [secdev/scapy](https://github.com/secdev/scapy) |
| **paramiko** | Python SSH implementation | [paramiko/paramiko](https://github.com/paramiko/paramiko) |

## Suggested "watch" shortlist

If you only follow a handful for release/patch monitoring: **nmap**, **Metasploit**, **hashcat**, **NetExec**, **impacket**, **Burp Suite**, **bettercap**.

> **Tip:** On each GitHub repo click **Watch → Custom → Releases**. You'll be notified only when a new release or security advisory drops — no commit spam.
