# OPNsense VLAN Segmentation — Live Config & Plan

> **Source of truth:** Scanned directly from OPNsense `config.xml` on 2026-08-27.
> VLANs are **defined** in OPNsense but **not yet in service** — no DHCP scopes,
> no inter-VLAN firewall rules, and the VLAN sub-interfaces are not bound to a
> parent NIC (`vlan01`–`vlan07` show `parent: <none>`). This doc records the
> intended scheme and what remains to wire up.

---

## 1. Live OPNsense Config (as scanned)

### Interfaces
| Interface | OPNsense name | Physical NIC | IP | Notes |
|-----------|---------------|--------------|-----|-------|
| WAN | `wan` | `em0` | DHCP | Internet uplink |
| LAN | `lan` | `igc0` | 10.2.7.1/24 | Main homelab subnet (currently flat) |
| Loopback | `lo0` | `lo0` | — | Management |

### VLANs — Defined but NOT yet bound
All VLAN sub-interfaces (`vlan01`–`vlan07`) are created on parent NIC **`re0`**
(Intel i210 — a separate LAN port, currently not carrying any IP). They exist in
config but are **not assigned/up** yet — `ifconfig` shows `vlan: 0 parent: <none>`.

| VLAN ID | OPNsense iface | Name | Gateway/Subnet | Parent NIC | Status |
|---------|----------------|------|----------------|------------|--------|
| 10 | `vlan01` / `opt1` | MGMT | 10.2.10.1/24 | `re0` | Defined, not bound |
| 20 | `vlan02` / `opt2` | SERVICES | 10.2.20.1/24 | `re0` | Defined, not bound |
| 30 | `vlan03` / `opt3` | SECURITY | 10.2.30.1/24 | `re0` | Defined, not bound |
| 40 | `vlan04` / `opt4` | MEDIA | 10.2.40.1/24 | `re0` | Defined, not bound |
| 50 | `vlan05` / `opt5` | CLIENT | 10.2.50.1/24 | `re0` | Defined, not bound |
| 60 | `vlan06` / `opt6` | IOT | 10.2.60.1/24 | `re0` | Defined, not bound |
| 70 | `vlan07` / `opt7` | LAB | 10.2.70.1/24 | `re0` | Defined, not bound |

### What is NOT configured yet
- ❌ **DHCP scopes** — `dhcpd` has no `<range>` per VLAN; nothing hands out IPs yet
- ❌ **Firewall rules** — zero `<rule>` entries; no inter-VLAN allow/deny logic
- ❌ **VLAN binding** — sub-interfaces not attached to `re0` parent yet

---

## 2. Intended Device Placement

| VLAN | Name | Devices |
|------|------|---------|
| 10 | MGMT | PVE1, PVE2, OPNsense mgmt, managed switch, PBS |
| 20 | SERVICES | Pi-hole (CT107 + 2× Pi), Gitea, Grafana, NPM, Uptime Kuma |
| 30 | SECURITY | Wazuh, Zeek, SIEM/dashboard |
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
4. **Move the media server CT onto the home WiFi VLAN** so TVs can still connect:
   - Either place the media CT on **MEDIA (40)** directly, **or** keep it isolated and
     open a single firewall rule: `CLIENT/MEDIA → media CT : allow TCP 8096 (+ Seerr port)`.
   - The firewall-rule approach keeps the server segmented; the direct-placement
     approach is simpler but shares the segment with family devices.

---

## 4. Remaining Work (to make VLANs live)

1. **Bind VLAN sub-interfaces** to `re0` parent in OPNsense
   (Interfaces → Other Types → VLAN → set parent `re0` for each; they're staged).
2. **Add DHCP scopes** per VLAN (MGMT 10, SERVICES 20, SECURITY 30, MEDIA 40,
   CLIENT 50, IOT 60, LAB 70). DNS = the two Pi-hole addresses.
3. **Write inter-VLAN firewall rules** (default deny, allow specific):
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
2. All devices reconnect on the original 10.2.7.0/24 subnet.
3. Remove VLAN interfaces from OPNsense.
4. Revert PVE `/etc/network/interfaces`.
5. Done — no lasting damage.

---

## 6. DR Backup

```bash
ssh root@10.2.7.1 'cat /conf/config.xml' > opnsense-backup-$(date +%F).xml
# Restore: System → Configuration → Backups → Upload
```

> **Note:** OPNsense SSH host key changed; connect with host-key checking disabled
> or update `known_hosts`. SSH root password = web UI admin password.
