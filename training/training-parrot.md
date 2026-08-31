# Parrot OS Quick Start — Security Testing Workbench

*Parrot Security Edition on a dedicated container (CT 145).*

---

## 1. What Parrot OS Actually Is (the mental model)

Parrot OS is a **security testing distribution** — Debian underneath, with hundreds of penetration-testing tools pre-installed. It's the **offense** side of security learning, paired with a SIEM (e.g. Wazuh) as the **defense** side:

- **SIEM** = watches what's happening and alerts you (the security camera).
- **Parrot** = the tool you use to *probe, scan, and test* your own systems (the flashlight + lock-pick set).

You run scans and tests **against your own lab**, and watch them light up in the SIEM. That's how you learn to see attacks from both sides.

Think of the desktop like a **workbench**: a dedicated machine, always ready, with every tool on the shelf, so you never install tools on your daily-driver PC.

---

## 2. Getting In

| Method | How | Best for |
|--------|-----|----------|
| **Browser (noVNC)** | Point a browser at the box's noVNC URL | Quick access from any browser |
| **RDP** | Connect to the box's RDP port from your desktop | Full desktop, more responsive |
| **SSH** | Headless terminal access | Scripting / automation |

> First time in noVNC: a connection prompt appears — enter the VNC password, then the Xfce desktop loads. Takes ~30s on first render.

---

## 3. What You're Looking At (the desktop)

You're on **Xfce** — a lightweight, fast desktop. The things that matter for security work:

- **Terminal** (top bar, or right-click → Open Terminal) — your main tool. Every security tool is a terminal command.
- **Application menu** (top-left) → browse categories. Security tools live under **Security / System / Network**.
- The login user has **`sudo`** — use `sudo <command>` when a tool needs root.

The full security toolset is installed (~3500 packages). You only need a handful at first (Section 5).

---

## 4. A Beginner Routine (build the habit)

Start with one thing per session. Twenty minutes is plenty:

1. **Boot it up**, open the terminal.
2. Run one scan against your own lab (Section 5).
3. **Cross-check in the SIEM** — the same traffic should appear as events there.
4. Close up. You're practicing the analyst loop: **act → observe → explain**.

> **Safety rule:** only scan/attack systems you own. Never point tools at things you don't control.

---

## 5. First Commands — the tools you'll actually use

### Recon / scanning
```bash
nmap -sn 10.0.0.0/24        # ping sweep — what's alive?
nmap -sV <target-ip>         # version scan a target
nmap -p- <target-ip>         # scan ALL ports on a target
```

### Password / hash cracking (learn the concept)
```bash
echo '5f4dcc3b5aa765d61d8327deb882cf99' > /tmp/hash.txt   # "password" as MD5
hashcat -m 0 /tmp/hash.txt /usr/share/wordlists/rockyou.txt
```

### Web testing
```bash
burpsuite                    # GUI — intercept HTTP requests
```

### Help / finding tools
```bash
apt search <toolname>        # find a tool in the repos
sudo apt install <tool>      # install more
```

> **Big one:** `msfconsole` (Metasploit) is installed but advanced — don't start there. Learn **nmap → hashcat → Burp** first. They build the fundamentals (recon, cracking, web).

---

## 6. Don't Panic Rules

- **You can't break your homelab from Parrot.** It's an isolated container — worst case you restart it. Your other services and data are untouched.
- **Tools can be loud.** `nmap` against your whole subnet will trigger SIEM alerts. That's *expected* — it's the point.
- **"Command not found"?** Not all tools are in `PATH`. Try `sudo apt install <tool>` or search the menu.
- **Desktop feels slow first load?** First render of the Xfce desktop + noVNC is slow (~30s). It's not broken.
- **noVNC blank screen?** The VNC session died — restart the VNC + noVNC services on the container.

---

## 7. Quick Reference Card

| I want to… | Do this |
|---|---|
| Open a terminal | Right-click desktop → Open Terminal, or top bar terminal icon |
| Find what's alive on my network | `nmap -sn 10.0.0.0/24` |
| Scan a specific box | `nmap -sV <target-ip>` |
| Crack a password hash | `hashcat -m 0 /tmp/hash.txt /usr/share/wordlists/rockyou.txt` |
| Intercept web traffic | `burpsuite` |
| Install a missing tool | `sudo apt install <tool>` |
| SSH in headless | `ssh` to the container's address |

---

*Generated for a self-hosted homelab. Parrot Security Edition, Xfce desktop (noVNC + RDP). Pair with the SIEM docs to practice the analyst loop.*
