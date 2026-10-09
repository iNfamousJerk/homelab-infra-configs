# VLAN Inter-Firewall Rule Matrix

> **Purpose:** The single source of truth for what each VLAN can reach.
> Default stance is **block all inter-VLAN**; only these rules open paths.
> Status: VLANs bound to `igc0` (LAN) on OPNsense; rules R1-R11 + per-interface
> default-deny implemented 2026-09-25. LAB (70) live (internet yes, internal blocked).
> CLIENT (50) in progress (AP on VLAN, switch port forwarding pending).
> Built 2026-09-22, updated 2026-09-25.

## Rule Matrix

| # | Source iface | Source net | Destination | Port | Action | Purpose |
|---|--------------|------------|-------------|------|--------|---------|
| 1 | MGMT (10) | 10.0.10.0/24 | Any | Any | ALLOW | Admin access everywhere |
| 2 | SERVICES (20) | 10.0.20.0/24 | Any | Any | ALLOW | Services reach out |
| 3 | Any | Any | Pi-hole (10.0.7.2) | UDP 53 | ALLOW | DNS for all VLANs |
| 4 | CLIENT (50) | 10.0.50.0/24 | WAN | Any | ALLOW | Internet |
| 5 | CLIENT (50) | 10.0.50.0/24 | MEDIA host | TCP 8096 | ALLOW | Jellyfin |
| 6 | CLIENT (50) | 10.0.50.0/24 | MEDIA host | TCP 5055 | ALLOW | Seerr |
| 7 | MEDIA (40) | 10.0.40.0/24 | MEDIA host | TCP 8096 | ALLOW | Jellyfin (Home-TV) |
| 8 | MEDIA (40) | 10.0.40.0/24 | MEDIA host | TCP 5055 | ALLOW | Seerr (Home-TV) |
| 9 | MEDIA (40) | 10.0.40.0/24 | WAN | Any | ALLOW | Downloads |
| 10 | IOT (60) | 10.0.60.0/24 | WAN | Any | ALLOW | Internet only, no LAN |
| 11 | LAB (70) | 10.0.70.0/24 | WAN | Any | ALLOW | Updates (isolated range) |
| 12 | any | Any | Any | Any | DENY | Default, last rule |
| 13 | floating | Any | Any | established | ALLOW | Return traffic |

## Key Posture Notes
- **IOT (60)** is internet-only — cannot reach any internal device. Quarantine.
- **LAB (70)** is outbound-only — nothing can reach INTO the practice range.
- **SERVICES (20)** carries services that reach out; DNS (Pi-hole) lives on the flat
  LAN at `10.0.7.2` (CT107) and is reachable from every VLAN via the floating DNS rule.
- **MEDIA host** = the CT running Jellyfin/Seerr (CT117). If the media CT is later
  moved onto MEDIA (40), rules 5-6 become unnecessary (same segment).
- **MGMT (10)** = admin only (PVE, PBS, switch, OPNsense mgmt).

## Apply Order (during migration)
1. Apply ALLOW rules (1-11, 13) FIRST — so services work as they move.
2. Move services onto their VLANs (re-IP).
3. Verify each service.
4. Apply the default DENY (12) last to lock it down.