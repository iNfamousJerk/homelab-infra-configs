# OPNsense VLAN Segmentation — Live Config & Plan

> **Source of truth:** Scanned directly from OPNsense `config.xml` on 2026-08-27,
> with live gateways verified 2026-09-24.
> VLANs are **bound and live** — all 7 gateways (10.0.10.1–10.0.70.1) answer on
> their sub-interfaces. They do **not yet provide isolation**: no hosts have
> migrated (each subnet contains only its `.1` gateway), no DHCP scopes, and
> no inter-VLAN firewall rules. VLANs currently route with **no isolation**.
> This doc records the scheme and what remains to wire up.

---

## 1. Live OPNsense Config (as scanned)

### Interfaces
| Interface | OPNsense name | Physical NIC | IP | Notes |
|-----------|---------------|--------------|-----|-------|
| WAN | `wan` | `em0` | DHCP | Internet uplink |
| LAN | `lan` | `igc0` | 10.0.7.1/24 | Main homelab subnet (currently flat) |
| Loopback | `lo0` | `lo0` | — | Management |

### VLANs — Bound and live (gateways up)
All 7 VLAN sub-interfaces (`vlan01`–`vlan07`) are bound to parent NIC **`re0`** and
assigned. Each gateway (10.0.10.1–10.0.70.1) answers as OPNsense. **No hosts have
migrated yet** — every subnet contains only its `.1` gateway.

| VLAN ID | OPNsense iface | Name | Gateway/Subnet | Parent NIC | Status |
|---------|----------------|------|----------------|------------|--------|
| 10 | `vlan01` / `opt1` | MGMT | 10.0.10.1/24 | `re0` | Bound, gateway live |
| 20 | `vlan02` / `opt2` | SERVICES | 10.0.20.1/24 | `re0` | Bound, gateway live |
| 30 | `vlan03` / `opt3` | SECURITY | 10.0.30.1/24 | `re0` | Bound, gateway live |
| 40 | `vlan04` / `opt4` | MEDIA | 10.0.40.1/24 | `re0` | Bound, gateway live |
| 50 | `vlan05` / `opt5` | CLIENT | 10.0.50.1/24 | `re0` | Bound, gateway live |
| 60 | `vlan06` / `opt6` | IOT | 10.0.60.1/24 | `re0` | Bound, gateway live |
| 70 | `vlan07` / `opt7` | LAB | 10.0.70.1/24 | `re0` | Bound, gateway live |

### What is NOT configured yet
- ❌ **DHCP scopes** — `dhcpd` has no `<range>` per VLAN; nothing hands out IPs yet
- ❌ **Firewall rules** — zero `<rule>` (committed config); VLANs route with no isolation
- ⚠️ **Management exposure** — OPNsense web/SSH (22/443) listen on every VLAN interface (see VLAN-RUNBOOK Phase 1c)

---

## 2. Intended Device Placement

| VLAN | Name | Devices |
|------|------|---------|
| 10 | MGMT | PVE1, PVE2, OPNsense mgmt, managed switch, PBS |
| 20 | SERVICES | Pi-hole (CT107 + 2× Pi), Gitea, Grafana, NPM, Uptime Kuma |
| 30 | SECURITY | osquery/Fleet, SIEM/dashboard |
| 40 | MEDIA | Jellyfin (CT117), Seerr, Immich, media stack — **also home WiFi media** |
| 50 | CLIENT | Gaming PC, wired desktops, phones/laptops on home SSID |
| 60 | IOT | Smart home, guest WiFi, Omada AP guest SSID |
| 70 | LAB | DC-2025, WIN-CLIENT, training VMs |

---

## 3. Current Network Plan (family vs server)

**Goal:** separate family devices from the homelab server while keeping everyone
behind OPNsense (single firewall), and let TVs reach the media server.

### The plan
1. **OPNsense** stays the edge router/firewall (VLAN routing, DHCP, rules).
2. **Omada AP** provides Wi-Fi with **per-SSID → VLAN** tagging:
   - `Home` SSID → **CLIENT (50)**
   - `Home-TV` / media SSID → **MEDIA (40)** (so TVs reach Jellyfin/Seerr)
   - `Guest` / `IoT` SSID → **IOT (60)** (internet only)
3. **Two Raspberry Pi (Pi-hole)** on the SERVICES/DNS path for **redundant DNS**,
   independent of PVE1 — so family streaming keeps resolving when the server is down.
   - Decommission CT107 Pi-hole once the Pis are live.
4. **Move the media server CT** — **DECISION (2026-08-27): Option A — keep the media
   CT isolated and open a firewall rule.** Do NOT move CT117 onto the MEDIA VLAN.
   Add rule: `CLIENT/MEDIA → CT117 : allow TCP 8096 (Jellyfin) + 5055 (Seerr)`.
   This keeps the server segmented from family streaming devices while letting
   TVs reach it.

---

## 4. Remaining Work (to make VLANs provide isolation)

1. ✅ **Bind VLAN sub-interfaces** to `re0` parent — **DONE** (all 7 gateways live).
2. **Add DHCP scopes** per VLAN (MGMT 10, SERVICES 20, SECURITY 30, MEDIA 40,
   CLIENT 50, IOT 60, LAB 70). DNS = the two Pi-hole addresses.
3. **Write inter-VLAN firewall rules** (default deny, allow specific) — see
   VLAN-RUNBOOK Phase 1c for the rule set and ordering:
   - MGMT → any: allow (admin access)
   - All VLANs → SERVICES : allow UDP 53 (DNS to Pi-hole)
   - CLIENT/MEDIA → MEDIA host : allow TCP 8096 (Jellyfin), + Seerr port
   - IOT → WAN only : allow (internet, no LAN)
   - Everything else : deny
4. **Configure the managed switch** for 802.1Q VLAN trunks (PVE1, PVE2, OPNsense,
   AP ports carry the VLANs; access ports get PVID).
5. **Make PVE bridges VLAN-aware** and assign VLAN tags to CTs/VMs.
6. **Deploy + configure the two Pi-holes**, set up gravity sync, point DHCP at them,
   then decommission CT107.
7. **Deploy the Omada AP**, tag SSIDs to VLANs.
8. **Move media CT** per decision in §3.

---

## 5. Rollback Plan

If VLAN migration breaks connectivity:
1. Disable 802.1Q VLAN on the switch → reverts to flat switch immediately.
2. All devices reconnect on the original 10.0.7.0/24 subnet.
3. Remove VLAN interfaces from OPNsense.
4. Revert PVE `/etc/network/interfaces`.
5. Done — no lasting damage.

---

## 6. DR Backup

```bash
ssh root@10.0.7.1 'cat /conf/config.xml' > opnsense-backup-$(date +%F).xml
# Restore: System → Configuration → Backups → Upload
```

> **Note:** OPNsense SSH host key changed; connect with host-key checking disabled
> or update `known_hosts`. SSH root password = web UI admin password.
