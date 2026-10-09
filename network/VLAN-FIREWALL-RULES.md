# OPNsense VLAN Firewall Ruleset — Phase 1c (PLAN ONLY)

> **⚠️ State plainly:** The **live rule set could not be read** from this host
> (no OPNsense credentials available here). This plan is built from the
> **committed `network/opnsense-config.xml`** — which contains **0 `<rule>` and 0
> `<range>`** — plus the observation that **no host has migrated** (every VLAN
> subnet contains only its `.1` gateway). **The operator must confirm the live
> rules in the OPNsense Web UI before moving any device.**
>
> Current exposure being mitigated: the 7 VLANs route with **no isolation**, and
> OPNsense management (TCP 22/443) listens on **every** VLAN interface. Moving
> devices onto a VLAN in this state — IoT (60) especially — is *worse* than the
> flat network, because those devices would reach every segment **and** the
> firewall's own management plane.

---

## 1. Management restriction (do this FIRST, and get it right)

Lock OPNsense's own web/SSH (TCP 443/22) to the MGMT range only. Applied on every
interface OPNsense listens on (LAN + each VLAN).

**Evaluation order — these go at the very top of the rule list on each interface:**

| # | Interface | Source | Destination | Port | Action | Note |
|---|-----------|--------|-------------|------|--------|------|
| M1 | LAN (10.0.7.0/24) | `10.0.7.0/24` | OPNsense IPs | 22,443 | **Allow** | **Anti-lockout**: keeps your current vantage reachable *during* the change |
| M2 | LAN (10.0.7.0/24) | `10.0.10.0/24` (MGMT) | OPNsense IPs | 22,443 | **Allow** | Intended permanent admin path |
| M3 | VLAN 10 MGMT | `10.0.10.0/24` | OPNsense IPs | 22,443 | **Allow** | Management inside its own VLAN |
| M4 | (all other VLANs) | Any | OPNsense IPs | 22,443 | **Deny** | Lock mgmt off SERVICES/IOT/CLIENT/etc. |
| M5 | (any) | Any | OPNsense IPs | Any | **Deny** | Belt-and-braces: nothing else reaches the firewall |

**⚠️ Lockout risk & anti-lockout:** the **M1 rule is your anti-lockout** — it must
exist *below* nothing (it is the highest-priority allow) and must be in place
BEFORE M4/M5 are added. If you are currently reaching OPNsense from a device
outside `10.0.7.0/24` or `10.0.10.0/24`, add an explicit per-IP allow for that
source first. If you get locked out, recover via **console/VGA on OPNsense**
(Firewall → Rules → temporarily disable the mgmt rule) — plan that access path
before you click Apply.

---

## 2. Default-deny inter-VLAN ruleset (Phase 1c)

Implements the Phase-1c stance: **allow only the documented paths, deny everything
else.** Each VLAN gets its own rule list; OPNsense evaluates top-down, **first
match wins**.

The deny-all default is expressed as an **explicit last rule per interface** so
the posture does not depend on OPNsense's implicit policy:

| # | Interface (source) | Source | Destination | Port/Proto | Action | Purpose |
|---|--------------------|--------|-------------|-----------|--------|---------|
| R1 | MGMT (10) | `10.0.10.0/24` | Any | Any | **Allow** | Admin can go anywhere |
| R2 | SERVICES (20) | `10.0.20.0/24` | Any | Any | **Allow** | Services reach out (updates, GitHub, indexers) |
| R3 | Any VLAN | Any | Pi-hole `10.0.20.53` / `10.0.20.54` | UDP 53 | **Allow** | DNS for all VLANs |
| R4 | CLIENT (50) | `10.0.50.0/24` | WAN | Any | **Allow** | Internet |
| R5 | CLIENT (50) | `10.0.50.0/24` | MEDIA host | TCP 8096 | **Allow** | Jellyfin |
| R6 | CLIENT (50) | `10.0.50.0/24` | MEDIA host | TCP 5055 | **Allow** | Seerr |
| R7 | MEDIA (40) | `10.0.40.0/24` | MEDIA host | TCP 8096 | **Allow** | Jellyfin (Home-TV) |
| R8 | MEDIA (40) | `10.0.40.0/24` | MEDIA host | TCP 5055 | **Allow** | Seerr (Home-TV) |
| R9 | MEDIA (40) | `10.0.40.0/24` | WAN | Any | **Allow** | Downloads |
| R10 | IOT (60) | `10.0.60.0/24` | WAN | Any | **Allow** | Internet only — **no LAN** |
| R11 | LAB (70) | `10.0.70.0/24` | WAN | Any | **Allow** | Updates (isolated range) |
| R12 | *(every interface)* | Any | Any | Any | **Deny** | **Default deny — last rule everywhere** |
| R13 | `floating` | Any | Any | established | **Allow** | Stateful return traffic |

**Key posture notes**
- **IOT (60)** → WAN only, terminated by R12. It cannot reach *any* internal device
  or the firewall mgmt (M4/M5 block OPNsense). This is the quarantine posture.
- **LAB (70)** is outbound-only for updates; nothing reaches *into* it (R12).
- **SERVICES (20)** carries the DNS every other VLAN depends on (R3).
- **MEDIA host** = CT117 (Jellyfin/Seerr). If you later move it onto MEDIA (40),
  drop R5–R8 (same segment).
- **R12 on every interface** is what turns "routes with no isolation" into
  "default deny." Until R12 is on every VLAN list, VLANs remain open.

---

## 3. Apply order (so services keep working and you don't lock out)

1. **Snapshot/backup OPNsense config** (System → Configuration → Backup).
2. Confirm your **console access** path (lockout insurance).
3. Add **M1 + M2 + M3** (mgmt allows) and **Apply** — verify you still reach OPNsense.
4. Add all **R1–R13** allow rules and **Apply** — verify services still work.
5. Add **M4 + M5 + R12** (the denies) LAST and **Apply** — this is the moment the
   VLANs become isolated. Verify IoT still reaches WAN but cannot ping any LAN host.
6. Do **not** add the mgmt-denies before the mgmt-allows are confirmed working.

> **Real-device order:** keep devices on the flat 10.0.7.0/24 until the mgmt
> allows (step 3) are verified. The named targets above (Pi-hole, MEDIA host)
> assume they exist at the documented IPs; confirm before applying.
