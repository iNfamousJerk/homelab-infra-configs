# Proxmox VE Beginner's Manual — <username>'s Homelab
*Tailored to your actual setup.*

---

## 1. What Proxmox VE Actually Is (the mental model)

**Think of Proxmox as an apartment building manager for computers.**

You know how an apartment building has one structure but many separate units inside? Proxmox is that building. Your physical hardware (CPU, RAM, storage) is the building itself. Each "apartment" is either a **VM** (Virtual Machine — a full simulated computer with its own operating system) or an **LXC container** (a lightweight, shared-kernel unit that's more like renting a room inside an existing house).

**VM vs. LXC — Which is which?**
- **VM** = a full simulated PC. It has its own kernel, its own boot process, its own everything. Heavyweight but isolated. Think: "renting an entire house."
- **LXC Container** = shares the host's kernel but has its own filesystem and processes. It's faster, uses less RAM, and boots in seconds. Think: "renting a room — cheaper and cozy, but you share the house's plumbing."

In Anthony's lab, **everything runs as LXC containers** (CTs) except the router and storage boxes — lightweight is the name of the game.

---

## 2. Getting In

You have **two** Proxmox nodes. They are NOT clustered (they don't talk to each other).

### PVE1 — The Workhorse
- **URL:** https://10.x.x.xxx:8006
- **Login:** `root@pam` / `<password>`
- **Hardware:** HP ProDesk 400 G4 SFF, Intel i5-7500, 32GB DDR4 RAM, 1TB SSD
- **Proxmox Version:** PVE 9.2.3

### PVE2 — The Old Reliable
- **URL:** https://10.x.x.xxx:8006
- **Login:** `root@pam` / `<password>`
- **Hardware:** Custom-built, Intel i7-2600K, 16GB DDR3 RAM, ZFS pool (multiple drives)
- **Proxmox Version:** PVE 8.4.19

**Note:** Your browser will scream "Not Secure!" at the HTTPS. That's fine — it's a self-signed certificate. Click through anyway. We're in a homelab, not a bank.

---

## 3. What You're Looking At

When you log in, you'll see the **Datacenter view** — a tree on the left, panels on the right.

### The Left Tree
- **Datacenter** — the top level. Shows both nodes if they were clustered, but yours aren't.
- **pve1** (or whatever you named PVE1) — click to see your Proxmox host's summary
- **pve2** — same for the second node
- Under each node: the **CT list** (containers)

### The Dashboard Panels (Summary View)
- **CPU / Memory / Root** — real-time usage gauges. Green = fine. Red = call a doctor.
- **System** — hostname, uptime, kernel version
- **Proxmox version** — good to know if you need updates

### CT List (Your Containers)

**On PVE1:**
| CT ID | Name | What It Does |
|-------|------|-------------|
| 100 | hermesagent | The AI assistant itself |
| 102 | pialert | Network monitoring & alerts |
| 105 | wazuh | SIEM security monitoring |
| 106 | grafana | Metrics dashboards |
| 107 | pihole | DNS sinkhole & ad-blocking |
| 108 | portainer | Docker management UI |
| 109 | heimdall | Dashboard homepage |
| 113 | hermes-ollama | Local LLM (AI model hosting) |

**On PVE2:**
| CT ID | Name | What It Does |
|-------|------|-------------|
| 101 | zeek | Network security monitoring |
| 103 | ripper | Media ripping |
| 110 | media-stack | Plex / *arr services |
| 111 | immich | Photo backup & management |
| 112 | nextcloud | File sync & share |

---

## 4. How to Read the Metrics

### CPU Usage
The big number. If it's consistently above 80%, your container might need more cores. But in a homelab, at idle, most CTs sip 0-5%.

### Memory (RAM)
Your PVE1 with 32GB is your heavy lifter. Containers share RAM smartly — just because each CT shows 512MB allocated doesn't mean they're using it all. Look for the **used** column, not the **allocated** column.

### Disk I/O
If a VM/CT is slow and the I/O delay is red, your disk is the bottleneck. On PVE2, ZFS helps a lot here with caching.

### Uptime
How long since the container was last started. If a container keeps showing low uptime numbers (a few hours), something is crashing or rebooting — that's a problem to investigate.

---

## 5. A Beginner Routine

**Daily (30 seconds):**
1. Log into PVE1 (10.x.x.xxx:8006)
2. Glance at the Summary page — any CT showing red CPU/MEM? Any alert icons?
3. If you see CT105 (Wazuh), that's fine — we'll check that elsewhere.

**Weekly (2 minutes):**
1. Log into both PVE1 and PVE2
2. Check for updates: the "Updates" button on each node
3. Reboot any containers that show a nagging "restart required" — but only if you have time to verify they come back up
4. Check your ZFS pool health on PVE2 (Datacenter → pve2 → Disks → ZFS)

**Monthly (10 minutes):**
1. Run updates on both hosts (carefully — read the changelogs)
2. Verify all CTs are running and responding
3. Check disk space on both nodes — 1TB fills up faster than you think on PVE1
4. Check if you need to move any containers around for resource balance

---

## 6. Don't Panic Rules

- **"I accidentally stopped a container!"** Start it again from the CT list. Right-click → Start. Or highlight it and hit the green button. Your data is still there.
- **"The web UI is slow!"** It happens. Proxmox uses a lot of JavaScript. Refresh the page, wait 10 seconds, try again. Usually fine.
- **"I can't remember which node has which CT!"** That's why we have this doc. PVE1: CT100-113 (mostly). PVE2: CT101-112 (mostly). The CT IDs tell the story — look at the last octet.
- **"ZFS pool is DEGRADED!"** One drive failed. Don't panic — your data is still on the good drive. It means you need to replace the bad one. This is why you have a mirror.
- **"PVE1 is newer but smaller storage; PVE2 is older but has ZFS"** — that's by design. PVE1 runs your daily drivers (lightweight services), PVE2 runs your data-heavy services (media, photos, files). Use them as they're intended.

---

## 7. Quick Reference Card

| I want to... | Do this... |
|-------------|-----------|
| Start a container | Click the CT → "Start" button |
| Stop a container | Click the CT → "Stop" (graceful) or "Shutdown" |
| Open a shell in a CT | Click the CT → Console tab |
| See CT resource usage | Summary tab of the CT |
| Resize a CT's disk | CT → Hardware → Hard Disk → Resize |
| Check for updates | Node → Updates → Refresh → Upgrade |
| Reboot a Proxmox host | Node → Reboot (only if all VMs/CTs are stopped) |
| Check ZFS pool health | Node → Disks → ZFS |
| See what's running where | Datacenter → click each node → check CT list |

---

*Generated for <username>'s homelab.*
