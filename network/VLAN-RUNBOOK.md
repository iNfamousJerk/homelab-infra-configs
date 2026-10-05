# VLAN Migration Runbook — OPNsense + PVE + Switch

> **Purpose:** Step-by-step, copy-pasteable runbook to take the 7 VLANs from
> "defined but staged" to fully live. Built 2026-08-27 from live scans.
> **Status legend:** ⏳ not started · 🟡 partial · ✅ done

---

## 0. Current Reality (pre-flight scan, 2026-08-27)

| Layer | State |
|-------|-------|
| OPNsense VLANs 10–70 | ✅ Defined on `re0`, gateways 10.2.x.1/24 — but sub-interfaces show `parent: <none>`, **not bound/UP** |
| OPNsense DHCP | ❌ No scopes configured |
| OPNsense firewall | ❌ Zero rules |
| PVE1 bridge | 🟡 `vmbr0` has `bridge-vlan-aware yes` + `bridge-vids 2-4094`, but flat IP still on vmbr0 (no sub-interface) |
| PVE2 bridge | ❌ Not VLAN-aware (plain static `vmbr0`) |
| Managed switch | ⏳ Not located / not pinging (assume 802.1Q DISABLED / flat) |

**Gateway layout:**
```
VLAN 10 MGMT    10.2.10.1/24
VLAN 20 SERVICES 10.2.20.1/24
VLAN 30 SECURITY 10.2.30.1/24
VLAN 40 MEDIA    10.2.40.1/24
VLAN 50 CLIENT   10.2.50.1/24
VLAN 60 IOT      10.2.60.1/24
VLAN 70 LAB      10.2.70.1/24
```

---

## Phase 1 — OPNsense: bind VLANs + DHCP + firewall

### 1a. Bind VLAN sub-interfaces to parent `re0`
Web UI → **Interfaces → Other Types → VLAN**. For each existing VLAN (10–70),
set **Parent Interface = `re0`** (currently blank). Then **Interfaces → Assignments**:
make sure `opt1`–`opt7` map to `vlan01`–`vlan07`. Enable each interface.

### 1b. Add DHCP scopes (Services → DHCP Server → [each VLAN])
| VLAN | Enable | Range | DNS |
|------|--------|-------|-----|
| 10 MGMT | on | 10.2.10.100 – 10.2.10.200 | 10.2.20.53, 10.2.20.54 (Pi-hole) |
| 20 SERVICES | on | 10.2.20.100 – 10.2.20.200 | 10.2.20.53, 10.2.20.54 |
| 30 SECURITY | on | 10.2.30.100 – 10.2.30.200 | 10.2.20.53, 10.2.20.54 |
| 40 MEDIA | on | 10.2.40.100 – 10.2.40.200 | 10.2.20.53, 10.2.20.54 |
| 50 CLIENT | on | 10.2.50.100 – 10.2.50.200 | 10.2.20.53, 10.2.20.54 |
| 60 IOT | on | 10.2.60.100 – 10.2.60.200 | 10.2.20.53, 10.2.20.54 |
| 70 LAB | on | 10.2.70.100 – 10.2.70.200 | 10.2.20.53, 10.2.20.54 |

> **Note:** Pi-hole addresses above are placeholder until the two Pis get real
> static IPs. Update after Pi deployment. DNS to Pi-hole lives on SERVICES (20).

### 1c. Firewall rules (Firewall → Rules → [each VLAN], floating rules option)

**Default stance: block all inter-VLAN. Add only these:**

| # | Interface (source) | Source | Destination | Port | Action |
|---|-----|--------|-------------|------|--------|
| 1 | MGMT (10) | 10.2.10.0/24 | Any | Any | ✅ Allow |
| 2 | SERVICES (20) | 10.2.20.0/24 | Any | Any | ✅ Allow |
| 3 | Any → SERVICES | Any | 10.2.20.53/54 | UDP 53 | ✅ Allow (DNS) |
| 4 | CLIENT (50) | 10.2.50.0/24 | WAN | Any | ✅ Allow (internet) |
| 5 | CLIENT (50) | 10.2.50.0/24 | MEDIA host | TCP 8096 | ✅ Allow (Jellyfin) |
| 6 | CLIENT (50) | 10.2.50.0/24 | MEDIA host | TCP 5055 | ✅ Allow (Seerr) |
| 6b | MEDIA (40) | 10.2.40.0/24 | MEDIA host | TCP 8096 | ✅ Allow (Jellyfin, Home-TV) |
| 6c | MEDIA (40) | 10.2.40.0/24 | MEDIA host | TCP 5055 | ✅ Allow (Seerr, Home-TV) |
| 7 | MEDIA (40) | 10.2.40.0/24 | WAN | Any | ✅ Allow (downloads) |
| 8 | IOT (60) | 10.2.60.0/24 | WAN | Any | ✅ Allow (internet only) |
| 9 | LAB (70) | 10.2.70.0/24 | WAN | Any | ✅ Allow (updates) |
| 10 | (any) | Any | Any | Any | ❌ Deny (default, last rule) |
| 11 | (floating) | Any | Any | established | ✅ Allow (return traffic) |

**Media host** = the CT that runs Jellyfin/Seerr (currently CT117). If you move the
media CT onto MEDIA (40) directly, skip rules 5–6 (same segment) — the TV just
reaches it. Use the firewall-rule approach if you keep the server isolated.

---

## Phase 2 — PVE: make both bridges VLAN-aware

### 2a. PVE2 (not VLAN-aware yet) — edit `/etc/network/interfaces`
**Before:**
```
auto vmbr0
iface vmbr0 inet static
        address 10.2.7.62/24
        bridge-ports eno1
        bridge-stp off
        bridge-fd 0
```
**After:**
```
auto vmbr0
iface vmbr0 inet manual
        bridge-ports eno1
        bridge-stp off
        bridge-fd 0
        bridge-vlan-aware yes
        bridge-vids 2-4094

auto vmbr0.10
iface vmbr0.10 inet static
        address 10.2.10.62/24
        gateway 10.2.10.1
```
Then **reboot PVE2** (staggered — see quorum note below).

### 2b. PVE1 (already vlan-aware) — add sub-interface
`vmbr0` is already `bridge-vlan-aware yes`. Add the MGMT sub-interface and move
the flat IP:
```
auto vmbr0.10
iface vmbr0.10 inet static
        address 10.2.10.64/24
        gateway 10.2.10.1
```
> ⚠️ **Cluster quorum:** 2-node cluster. Reboot nodes ONE at a time, wait for full
> recovery before the next, or temporarily `pvecm delnode` to avoid the frozen UI.

### 2c. Assign VLAN tags to CTs/VMs
In PVE web UI → each VM/CT → Network → set **VLAN Tag** per the device map:
- MGMT (10): PVE hosts, PBS
- SERVICES (20): Pi-hole, Gitea, Grafana, NPM, Uptime Kuma, osTicket
- SECURITY (30): osquery/Fleet
- MEDIA (40): Jellyfin/Seerr (CT117), Immich, media CT
- CLIENT (50): — (physical devices)
- IOT (60): — (WiFi)
- LAB (70): DC-2025, WIN-CLIENT

---

## Phase 3 — Managed switch (TL-SG108E or similar)

### Port map (from reference)
| Port | Device | Mode | VLAN Membership | PVID |
|------|--------|------|-----------------|------|
| 1 | SPARE | — | — | — |
| 2 | OPNsense | Trunk | Tagged: 10,20,30,40,50,60,70 | 10 |
| 3 | SPARE | — | — | — |
| 4 | PBS | Trunk | Tagged: 10,20,30,40,50,60,70 | 10 |
| 5 | PVE2 | Trunk | Tagged: 10,20,30,40,50,60,70 | 10 |
| 6 | Gaming PC | Access | Untagged: 50 | 50 |
| 7 | Omada AP | Trunk | Tagged: 40,50,60 (+10/20 if needed) | 50 |
| 8 | PVE1 | Trunk | Tagged: 10,20,30,40,50,60,70 | 10 |

**Steps (TL-SG108E):**
1. **VLAN → 802.1Q VLAN → Enable** (reboots VLAN subsystem)
2. Create each VLAN ID (10,20,30,40,50,60,70) with port membership (Tagged/Untagged/Not Member) per table above
3. **VLAN → 802.1Q PVID Setting** — set each port's PVID per table
4. Apply
5. **Omada AP (port 7):** trunk — it does its own per-SSID tagging (Home→50, Media→40, Guest→60)

> **If you're not using the TL-SG108E**, the switch's web UI varies but the concepts
> are identical: enable 802.1Q, create VLANs, set trunk/access ports + PVIDs.

---

## Phase 4 — Omada AP + SSIDs

Create SSIDs in the Omada controller, each mapped to a VLAN network:

| SSID | VLAN | Audience | Can reach |
|------|------|----------|-----------|
| `Home` | 50 (CLIENT) | Phones, laptops | Internet, Jellyfin, Navidrome |
| `Home-TV` | 40 (MEDIA) | Smart TVs, Roku | Jellyfin, Seerr directly |
| `Guest` | 60 (IOT) | Visitors | Internet only 🔒 |

The AP tags client traffic per SSID on its trunk uplink (switch port 7).

---

## Phase 5 — Pi-hole redundancy (2× Raspberry Pi)

1. Install Pi-hole on both Pis (static IPs, e.g. `10.2.20.53` + `10.2.20.54`).
2. In OPNsense DHCP, set **both** as DNS for every VLAN scope (primary + secondary).
3. Sync blocklists between the two — Pi-hole **gravity sync** (Settings → Gravity
   sync, point each at the other) so both stay identical.
4. **Do NOT load-balance** — use primary/secondary failover only.
5. Point OPNsense's own DNS (Unbound) to forward to the Pi-holes or use them as upstream.
6. Once both Pis are live and answering, **decommission CT107** (`pct stop 107`, then
   remove or disable autostart).

---

## Phase 6 — Media server CT (DECISION 2026-08-27: **Option A**)

**Option A (SELECTED) — keep server isolated + firewall rule:**
Keep CT117 on its current network. Add firewall rules #5/#6 from Phase 1c:
`CLIENT (50) → CT117 : TCP 8096` (Jellyfin) and `TCP 5055` (Seerr). Also allow
`MEDIA (40) → CT117 : TCP 8096/5055` so Home-TV devices reach it.
TVs on Home-TV (40) reach Jellyfin through the firewall. The media server stays
segmented from family devices — selected over Option B (moving CT117 onto MEDIA).

---

## Phase 7 — Verification

- [ ] `ifconfig | grep vlan` on OPNsense → all vlan01–07 show `UP`, `parent: re0`, `status: active`
- [ ] Each VLAN gateway pings (10.2.10.1 … 10.2.70.1)
- [ ] DHCP hands out correct subnets (a client on each VLAN gets 10.2.X.x)
- [ ] Pi-hole resolves DNS from every VLAN (`pihole -a -i all`)
- [ ] SSH from MGMT to all VLANs works
- [ ] IoT cannot ping any internal device
- [ ] Gaming PC (CLIENT) reaches internet + Pi-hole only
- [ ] Jellyfin reachable from CLIENT/MEDIA (port 8096)
- [ ] Switch web UI reachable on MGMT

---

## Rollback

1. Disable 802.1Q VLAN on switch → flat switch, all devices reconnect on 10.2.7.0/24
2. Remove VLAN interfaces from OPNsense
3. Revert PVE `/etc/network/interfaces` (restore flat vmbr0)
4. Done — no lasting damage
