# Homelab Infrastructure Configurations

> 🏗️ **Public-ready reference configurations** for a self-hosted homelab stack.

This repository contains sanitized Docker Compose, monitoring, and reverse proxy configurations for a multi-service private infrastructure. All secrets, service names, and identifying details have been replaced with environment variables and generic enterprise terminology.

## Architecture Overview

| Layer | Services | Purpose |
|-------|----------|---------|
| **Hypervisor** | Proxmox VE (2-node cluster) + Proxmox Backup Server | LXC/VM hosting across dual hosts, ZFS backups |
| **Gateway/Firewall** | OPNsense | VLAN routing, firewall, DHCP, VPN |
| **DNS Filter** | Pi-hole + Unbound | Network-wide ad blocking, local DNS, recursive resolver |
| **VPN** | Tailscale | Secure mesh VPN for remote access |
| **Monitoring** | Prometheus, Grafana, Node Exporter, cAdvisor, Blackbox, Uptime Kuma | Metrics, alerting, dashboards |
| **Security Monitoring** | Wazuh SIEM + Zeek IDS sensor | Host & network threat detection, log analysis, ARP monitoring |
| **Source Control** | Gitea | Private git hosting |
| **Automation Agent** | Hermes Agent (primary + local LLM) | AI orchestration, cron jobs, Discord gateway |
| **Container Management** | Portainer CE | Container orchestration UI |
| **Service Dashboard** | Heimdall | Centralized bookmark & service dashboard |
| **Media Stack** | 18 Docker containers | Content ingestion, indexing, streaming (VPN-protected) |
| **Photo Management** | Immich | Self-hosted photo backup & management |
| **File Sync** | Nextcloud | File sync, share, and collaboration |
| **MDM** | MicroMDM | Apple device management (DEP, enrollment) |
| **IT Asset Management** | Snipe-IT | Hardware and software asset tracking |
| **Domain Services** | Windows Server 2025 AD | Domain controller, DNS, DHCP, GPO management |

## Hardware Layout

| Host | Type | Hardware | Storage |
|------|------|----------|---------|
| **Node A** (PVE) | Hypervisor | HP ProDesk 400 G4, Core i5-7500, 32GB RAM | 930GB SSD |
| **Node B** (PVE) | Hypervisor | Custom build, Core i7-2600K, 16GB RAM | 4×2TB ZFS pool (2.72TB usable) |
| **PBS Node** (PVE) | Backup Server | HP Z230, Xeon E3-1225 v3, 16GB RAM | ZFS storage |

## Active Container Reference

All containers use private RFC1918 addressing (10.x.x.x). No public IPs are exposed.

### Node A (10.2.7.x)

| Role | Hostname | CT | OS | vCPU | RAM | Disk | Notes |
|------|----------|----|----|------|-----|------|-------|
| AI Orchestration Agent | hermesagent | 100 | Debian 13 | 4 | 8GB | 30GB | Hermes Agent, Discord gateway, Node Exporter, Cockpit |
| Network Alerting | pialert | 102 | Debian 13 | 2 | 2GB | 10GB | PiAlert ARP monitoring, Node Exporter, Cockpit |
| SIEM Manager | wazuh | 105 | Debian 13 | 2 | 8GB | 50GB | Wazuh manager + indexer + dashboard, PatchMon |
| Monitoring Hub | grafana | 106 | Ubuntu 24.04 | 2 | 4GB | 30GB | Grafana, Prometheus, Gitea, Uptime Kuma, Snipe-IT — 13 Docker containers |
| DNS Filter | pihole | 107 | Debian 13 | 2 | 4GB | 4GB | Pi-hole + Unbound, Node Exporter, Cockpit |
| Container Management | portainer | 108 | Debian 12 | 1 | 1GB | 10GB | Portainer CE |
| Service Dashboard | heimdall-dashboard | 109 | Debian 13 | 1 | 1GB | 2GB | Heimdall dashboard |
| Local LLM Inference | hermes-ollama | 113 | Ubuntu 24.04 | 4 | 8GB | 40GB | Ollama (qwen2.5:3b), Node Exporter, Cockpit |
| Centralized Management | cockpit | 114 | Debian 12 | 2 | 2GB | 10GB | Cockpit node manager, Node Exporter |

### Node B (10.2.7.x)

| Role | Hostname | CT | OS | vCPU | RAM | Disk | Notes |
|------|----------|----|----|------|-----|------|-------|
| Network IDS Sensor | zeek | 101 | Debian 12 | 2 | 2GB | 12GB | Zeek passive traffic analysis on port-mirror |
| Media Automation | ripper | 103 | Debian 12 | 2 | 2GB | 20GB | DVD ripping, python3 automation |
| MDM Server | micromd | 104 | Debian 12 | 2 | 2GB | 20GB | MicroMDM (Apple device management), Docker |
| Media Stack Host | media-stack | 110 | Debian 12 | 4 | 8GB | 60GB | 18 Docker containers: Jellyfin, Sonarr, Radarr, etc., Vaultwarden, NPM |
| Photo Management | immich | 111 | Debian 13 | 2 | 4GB | 50GB | Immich + PostgreSQL + Redis, Node Exporter |
| File Sync & Share | nextcloud | 112 | Debian 12 | 2 | 4GB | 50GB | Nextcloud + MariaDB + Redis, Node Exporter |

## Virtual Machines

| Role | VM | OS | vCPU | RAM | Disk |
|------|----|----|------|-----|------|
| Domain Controller | 200 | Windows Server 2025 | 2 | 4GB | 40GB |
| Domain Client | 201 | Windows 11 | 2 | 4GB | 40GB |

## Active Directory Lab

| Component | Value |
|-----------|-------|
| Domain | homelab.local |
| Domain Controller | Windows Server 2025 (VM 200) |
| Services | AD DS, DNS, DHCP, GPOs |
| Organizational Units | Employees → IT, Computers, Groups |
| User Management | User accounts, group membership, domain join |
| Remote Management | WinRM |

## Media Stack — Enterprise Abstraction Reference

| Generic Name | Actual Software | Purpose |
|---|---|---|
| `vpn-gateway` | Gluetun | VPN tunnel (OpenVPN/WireGuard) |
| `ingress-transport-node` | qBittorrent | Torrent download client |
| `upstream-index-router` | Prowlarr | Indexer aggregation & searching |
| `content-aggregator` | Radarr | Film/feature content automation |
| `data-indexer-service` | Sonarr | Episodic content automation |
| `data-indexer-service-2` | Lidarr | Audio content automation |
| `subtitle-enrichment-service` | Bazarr | Subtitle acquisition & management |
| `internal-streaming-microservice` | Jellyfin | Media streaming server |
| `media-request-gateway` | Jellyseerr | Content request management |
| `captcha-resolver` | FlareSolverr | Cloudflare challenge bypass |
| `credential-vault` | Vaultwarden | Password management |
| `reverse-proxy` | Nginx Proxy Manager | SSL termination & domain routing |

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Linux (tested on Debian 12/13 and Ubuntu 24.04 LXC containers)
- A VPN subscription (for production media stack)
- A wildcard DNS record or Pi-hole local DNS override
- Proxmox VE 8.x+ (for cluster management)

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <this-repo> homelab-configs
cd homelab-configs

# 2. Copy and fill in secrets
cp .env.example .env
# Edit .env with your credentials

# 3. Install pre-commit hook (prevents accidental secret commits)
cp scripts/pre-commit-secret-scan.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 4. Deploy a stack
docker compose -f docker-compose.yml up -d              # Monitoring stack
docker compose -f media-stack.yml up -d                 # Media stack (prod)
```

## File Layout

```
.
├── docker-compose.yml              # Monitoring stack (Prometheus, Grafana, etc.)
├── media-stack.yml                 # Media stack — production (VPN-protected)
├── media-stack-testing.yml         # Media stack — testing (no VPN, local only)
├── nextcloud-office-stack.yml      # Office productivity stack
├── nginx-default.conf              # Nginx reverse proxy subdomain config
├── nginx.conf                      # Base nginx configuration
├── prometheus.yml                  # Prometheus scrape configuration
├── alertmanager.yml                # Alertmanager routing & receivers
├── homelab_alerts.yml              # Prometheus alerting rules
├── security-monitoring.md          # Zeek + Wazuh architecture reference
├── .env.example                    # Environment variable template
├── CREDENTIALS-TEMPLATE.md         # Credential tracking template (NEVER commit real creds)
└── scripts/
    ├── pre-commit-secret-scan.py   # Pre-commit hook for secret detection
    ├── homelab-panel.py            # Homelab monitoring panel
    ├── media-dash.py               # Media stack dashboard
    ├── dvd-webui.py                # DVD ripping web UI
    └── dvd-watchdog.sh             # DVD watchdog service
```

## Boot Order

### Node A (dependency-aware)

```
 1. DNS Filter (107)   — DNS first — everything needs DNS
 2. Monitoring Hub (106) — Grafana, Prometheus, Gitea, Uptime Kuma
 3. Network Alerting (102) — PiAlert
 4. Container Management (108) — Portainer
 5. Local LLM Inference (113) — Ollama cron worker
 6. Service Dashboard (109) — Heimdall
 7. SIEM Manager (105) — Wazuh
 8. AI Orchestration Agent (100) — starts once infra is ready
 9. Centralized Management (114) — Cockpit node manager
```

### Node B

```
 1. Network IDS Sensor (101)   — Zeek (passive capture, no dependencies)
 2. Photo Management (111)     — Immich
 3. File Sync & Share (112)    — Nextcloud
 4. MDM Server (104)           — MicroMDM
 5. Media Stack Host (110)     — heaviest, starts last (18 containers)
 6. Media Automation (103)     — DVD ripping
```

## Security

- **All secrets** are injected via `.env` files — never hardcoded
- **VPN kill switch** prevents IP leaks on VPN drop
- **Pre-commit hook** scans staged files for API keys, tokens, and credentials
- **`.gitignore`** blocks `.env`, `.pem`, `.key`, `config/` directories, and more
- **RFC1918 private IPs** only — no public WAN addresses exposed
- **Tailscale mesh VPN** for secure remote access without open ports

## Reference Documents

- **[Security Monitoring](./security-monitoring.md)** — Passive network IDS (Zeek) + Wazuh SIEM architecture, deployment principles, and log reference
- **[CREDENTIALS-TEMPLATE](./CREDENTIALS-TEMPLATE.md)** — Credential tracking template (DO NOT commit real values to public repos)