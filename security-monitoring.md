# Security Monitoring — Reference Architecture

> Sanitized reference. Passive network IDS and SIEM architecture for a self-hosted infrastructure. No real addresses or identifying details.

## Components

| Component | Software | Role |
|-----------|----------|------|
| **SIEM Manager** | Wazuh | Central log ingestion, rule-based detection, file integrity monitoring, vulnerability scanning |
| **SIEM Agents** | Wazuh agent | Per-host log/FIM/vulnerability shipping (one per container) |
| **Network IDS Sensor** | Zeek | Passive traffic analysis on a dedicated, isolated sensor node |

## Design Principles

1. **Passive, off-box network IDS.** The network sensor runs on its **own dedicated node** and analyzes a **mirrored copy** of traffic delivered via a managed switch's port-mirror (SPAN) feed. The capture interface is a separate physical NIC bridged in promiscuous mode with **no IP address** — the sensor cannot transmit on the monitored segment and **cannot affect the firewall or production traffic**.
   - *Rationale:* inline IDS/IPS that hooks the firewall packet path was explicitly rejected after repeated stability problems with firewall-based approaches. A passive sensor delivers visibility with zero blast radius.

2. **Unified pane.** Network IDS logs (connections, DNS, HTTP, TLS, notices, anomalies) are emitted as JSON and shipped via the SIEM agent into the same dashboard as host security events, enabling host+network correlation.

3. **Least exposure.** The sensor node carries only management + capture interfaces; no inbound services.

4. **Dual-host separation.** The sensor runs on a separate hypervisor node from the SIEM manager, ensuring that a compromise of either host does not eliminate both detection layers.

## Why Passive IDS (vs Inline / Firewall-Integrated)

| Approach | Blast Radius | Maintenance | Visibility |
|----------|-------------|-------------|------------|
| **Inline (Suricata/Snort on firewall)** | High — misconfiguration can drop all traffic | Requires firewall restarts, VLAN reconfig | Full (sees everything the firewall sees) |
| **Passive IDS (Zeek on mirror)** | **Zero** — sensor cannot affect production traffic | None on firewall; sensor is self-contained | Full (mirrors traffic at the switch level) |

The passive approach was chosen after inline solutions caused repeated firewall stability issues requiring full factory resets and infrastructure downtime.

## Network IDS Log Types (JSON → SIEM)

| Log | Question Answered | Key Fields |
|-----|-------------------|------------|
| `conn` | Who connected to whom, how much data | `id.orig_h`, `id.resp_h`, `id.resp_p`, `service`, `orig_bytes`, `resp_bytes`, `duration` |
| `dns` | What domains were resolved | `query`, `answers`, `rcode`, `qtype_name` |
| `http` | Cleartext web requests (methods, URIs, user-agents) | `host`, `uri`, `method`, `user_agent`, `status_code` |
| `ssl` | Encrypted endpoints identified by SNI | `server_name`, `issuer`, `id.resp_h`, `version` |
| `notice` | Sensor-flagged events (port scans, protocol violations) | `note`, `msg`, `sub`, `src`, `dst`, `p` |
| `weird` | Protocol anomalies (non-standard behavior) | `name`, `addl`, `peer` |
| `dhcp` | DHCP lease assignments | `client_addr`, `assigned_addr`, `host_name`, `domain` |
| `ntp` | NTP time synchronization queries | `client`, `server`, `mode`, `stratum` |

## Deployment Architecture

```
                    ┌─────────────────────┐
                    │   Managed Switch     │
                    │  (port-mirror/SPAN)  │
                    │  Uplink: WAN/LAN     │
                    └─────────┬───────────┘
                              │ mirrored traffic
                              ▼
              ┌───────────────────────────┐
              │   IDS Sensor (dedicated)  │
              │                           │
              │  eth0: management IP      │
              │  eth1: capture (no IP)    │
              │                           │
              │  ┌─────────────────────┐  │
              │  │  Zeek               │  │
              │  │  - conn.log         │──┼─── JSON logs
              │  │  - dns.log          │  │    │
              │  │  - http.log         │  │    │
              │  │  - ssl.log          │  │    │
              │  │  - notice.log       │  │    │
              │  │  - weird.log        │  │    │
              │  └─────────────────────┘  │    │
              └───────────────────────────┘    │
                                               │
                    ┌──────────────────────┐   │
                    │   SIEM Manager       │◄──┘
                    │   (Wazuh)             │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │ Dashboard       │  │
                    │  │ Alert Rules     │  │
                    │  │ Compliance      │  │
                    │  │ FIM Alerts      │  │
                    │  └─────────────────┘  │
                    └──────────────────────┘
```

## Log Flow

```
Switch port-mirror → IDS capture NIC (promiscuous)
         ↓
    Zeek parses traffic → JSON logs
         ↓
    SIEM agent tails log files → ships to Wazuh manager
         ↓
    Correlated with host-based events on Grafana dashboard
```

## Sensor Specifications

| Parameter | Value |
|-----------|-------|
| **OS** | Debian 12 LXC |
| **CPU** | 2 vCPUs |
| **RAM** | 2 GB |
| **Disk** | 12 GB |
| **Capture Interface** | Dedicated NIC, promiscuous mode, no IP address |
| **Management Interface** | Separate NIC, static IP on management VLAN |

## Deployment Steps (Abstracted)

1. **Provision the sensor node** — create a Debian 12 LXC with 2 vCPU / 2 GB RAM / 12 GB disk on the secondary hypervisor node.
2. **Configure capture interface** — assign the dedicated NIC to the container, set it promiscuous with no IP address via a oneshot systemd unit:
   ```bash
   # /etc/systemd/system/zeek-capture-iface.service
   [Unit]
   Description=Set Zeek capture interface to promiscuous mode
   After=network.target
   [Service]
   Type=oneshot
   ExecStart=/sbin/ip link set eth1 promisc on
   ExecStart=/sbin/ip addr flush dev eth1
   RemainAfterExit=yes
   [Install]
   WantedBy=multi-user.target
   ```
3. **Install Zeek** from the official upstream package repository (not distro packages).
4. **Enable JSON logging** — configure Zeek's `logging` script to emit JSON-formatted logs for all log streams.
5. **Install SIEM agent** on the sensor node. Add `localfile` entries in the agent config for each Zeek log path (`/opt/zeek/logs/current/*.log`).
6. **Configure switch port-mirror** — set the source as the gateway uplink segment (the VLANs to observe) and the destination as the switch port connected to the sensor's capture NIC.
7. **Verify log ingestion** — confirm that Zeek log lines appear in the Wazuh dashboard within minutes of traffic traversing the uplink.

## Planned Enhancements

- **Zeek intelligence framework** — feed threat intelligence (known C2 domains, malware hashes, phishing URLs) into Zeek for real-time matching against observed traffic
- **Custom Zeek scripts** — detect specific protocols or behaviors relevant to the environment (e.g., IoT device fingerprinting, unauthorized DNS tunneling)
- **Automated response** — trigger SIEM agent active response for high-severity network detections (e.g., isolate host communicating with known C2)
- **Traffic baseline modeling** — establish normal traffic patterns and alert on significant deviations