# Kali Lab — Hands-On Security Training

> Purpose: a **safe, isolated** playground to practice offensive techniques,
> packet/traffic analysis, and incident detection — the core skills for a SOC
> analyst role. The lab is segmented onto its own VLAN and deliberately has
> **no NPM / no external exposure**, so mistakes here cannot touch production.
>
> **Status 2026-09-27:** LAB VLAN (70) bound, gateway live, firewall = outbound
> internet only (default-deny last). All three lab hosts online on PVE3.

## Why a dedicated lab VLAN

Everything else on the homelab is production — your media stack, family-facing
SSO, monitoring. Practicing real attacks there would be reckless (and could
take down family Jellyfin/Immich). The LAB VLAN (10.0.70.0/24) gives you a
firewalled sandbox where an active attack, a misconfig, or a cone of silence
affects only the lab. It's the same reasoning as the passive Zeek sensor: the
blast radius of a mistake is zero.

## Inventory (PVE3)

| Host | ID | IP (VLAN 70) | Role |
|------|-----|--------------|------|
| Kali | VM 200 | 10.0.70.10 | Attacker / analyst box — your daily driver for the lab |
| Target | CT 201 | 10.0.70.20 | Vulnerable target (DC-2025 / WIN-CLIENT style) |
| Sensor | CT 202 | 10.0.70.30 | Passive Zeek network sensor |

- **Gateway:** 10.0.70.1 (OPNsense, `vlan07` / opt7)
- **DNS:** 10.0.7.2 (Pi-hole)
- **Network:** 10.0.70.0/24, 802.1Q tag 70

## Access

Kali uses cloud-init: user `kali`, SSH key auth from the hermes agent key.
From any host that holds the key:

```
ssh kali@10.0.70.10
```

The lab is only reachable from inside the lab VLAN (target/sensor) — you
generally stage your analysis on Kali and drive it from there.

## Lab workflows mapped to your SOC goals

Your stated direction: SOC analyst, packet/traffic analysis. The lab turns
that from theory into reps. Every session should be an attack-observed loop:

1. **Generate traffic** from Kali (scan, exploit, or normal-ish traffic).
2. **See it at the sensor** (CT 202, Zeek) and in the SIEM.
3. **Correlate** host events (Kali) + network logs (sensor) + firewall states.

### Packet analysis (Kali side)

```sh
# capture a specific host pair for study
sudo tcpdump -i eth0 -nn -s0 host 10.0.70.20 -w /tmp/capture.pcap

# read it back cleanly
sudo tcpdump -nn -r /tmp/capture.pcap

# interactive protocol drill-down
sudo tshark -r /tmp/capture.pcap -Y "http" # filter to a protocol
sudo tshark -r /tmp/capture.pcap -T fields -e ip.src -e ip.dst -e tcp.dport
```

### Zeek side (CT 202)

Zeek logs (conn, dns, http, tls, notices) stream as JSON to the SIEM. When you
fire a scan at the target, that activity lands in `conn.log` and surfaces in
the Wazuh dashboard — the exact "host+network correlation" a SOC analyst does.

## Current state / next steps

- Lab is reachable and isolated; all three hosts up.
- Zeek sensor on CT 202 is the **passive IDS roadmap item** noted in
  `security-monitoring.md` — driving it as part of the lab is the natural
  next upgrade so you get live network visibility during exercises.

> Keep the lab **off** the migration critical path — it stays on VLAN 70 and
> does not depend on NPM/DNS/arr service moves.
