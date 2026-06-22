# Homelab Infrastructure Configurations

> 🏗️ **Public-ready reference configurations** for a self-hosted homelab stack.

This repository contains sanitized Docker Compose, monitoring, and reverse proxy configurations for a multi-service private infrastructure. All secrets, service names, and identifying details have been replaced with environment variables and generic enterprise terminology.

## Architecture Overview

| Layer | Services | Purpose |
|-------|----------|---------|
| **Hypervisor** | Proxmox VE (cluster) + PBS | LXC container hosting across dual hosts, ZFS backups |
| **Gateway/Firewall** | OPNsense | VLAN routing, firewall, DHCP |
| **DNS Filter** | Pi-hole | Network-wide ad blocking, local DNS |
| **Monitoring** | Prometheus, Grafana, cAdvisor, Blackbox, Uptime Kuma | Metrics, alerting, dashboards |
| **Security Monitoring** | Wazuh SIEM + passive network IDS sensor | Host & network threat detection, log analysis |
| **Source Control** | Gitea | Private git hosting |
| **Automation Agent** | Hermes (primary + local LLM) | AI orchestration, cron jobs, Discord gateway |
| **Media Stack** | See below | Content ingestion, indexing, streaming |
| **Office Stack** | Vaultwarden, OnlyOffice, LanguageTool, Actual Budget | Self-hosted productivity |

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

## Infrastructure Layout

| Host | Type | Hardware | Containers |
|------|------|----------|------------|
| **Node A** (PVE 9.x) | Hypervisor | i5-7500, 32GB RAM, 930GB SSD | AI agent, DNS, monitoring, SIEM, dashboards, Portainer |
| **Node B** (PVE 8.x) | Hypervisor | i7-2600K, 16GB RAM, 2.72TB ZFS pool | Media stack, Zeek sensor, Immich, Nextcloud |

## Active Container Reference

| Role | Host | OS | Cores | RAM | Disk | Purpose |
|------|------|-----|-------|-----|------|---------|
| **AI Agent (primary)** | Node A | Debian 13 | 4 | 4GB | 30GB | Main automation agent, Discord gateway |
| **Local LLM Agent** | Node A | Ubuntu 24.04 | 4 | 8GB | 40GB | Ollama-based cron execution (0 API credits) |
| **DNS Filter** | Node A | Debian 13 | 2 | 4GB | 4GB | Pi-hole network DNS & ad blocking |
| **SIEM Manager** | Node A | Debian 12 | 2 | 8GB | 50GB | Wazuh security event management |
| **Monitoring Hub** | Node A | Ubuntu 24.04 | 2 | 4GB | 30GB | Grafana, Prometheus, Gitea, 10 Docker services |
| **Docker Management** | Node A | Debian 12 | 1 | 1GB | 10GB | Portainer UI across hosts |
| **Service Dashboard** | Node A | Debian 13 | 1 | 512MB | 2GB | Heimdall bookmark dashboard |
| **Network Alerting** | Node A | Debian 12 | 2 | 2GB | 10GB | PiAlert ARP-based device discovery |
| **Network IDS Sensor** | Node B | Debian 12 | 2 | 2GB | 12GB | Zeek passive traffic analysis (port-mirror feed) |
| **Media Stack** | Node B | Debian 13 | 4 | 8GB | 60GB | 13 Docker containers — VPN-protected media pipeline |
| **Photo Vault** | Node B | Debian 13 | 2 | 4GB | 50GB | Immich photo management (native) |
| **File Sync** | Node B | Debian 12 | 2 | 4GB | 50GB | Nextcloud with PostgreSQL |

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Linux (tested on Debian 12 LXC containers)
- A VPN subscription (for production media stack)
- A wildcard DNS record or Pi-hole local DNS override

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
├── nextcloud-office-stack.yml      # Office productivity stack
├── nginx-default.conf              # Nginx reverse proxy subdomain config
├── nginx.conf                      # Base nginx configuration
├── prometheus.yml                  # Prometheus scrape configuration
├── alertmanager.yml                # Alertmanager routing & receivers
├── homelab_alerts.yml              # Prometheus alerting rules
├── .env.example                    # Environment variable template
├── CREDENTIALS-TEMPLATE.md         # Credential tracking template (NEVER commit real creds)
└── scripts/
    └── pre-commit-secret-scan.py   # Pre-commit hook for secret detection
```

## Security

- **All secrets** are injected via `.env` files — never hardcoded
- **VPN kill switch** prevents IP leaks on VPN drop
- **Pre-commit hook** scans staged files for API keys, tokens, and credentials
- **`.gitignore`** blocks `.env`, `.pem`, `.key`, `config/` directories, and more
- **RFC1918 private IPs** only — no public WAN addresses exposed

## Boot Order (Node A — dependency-aware)

```
1. DNS Filter (DNS first — everything needs DNS)
2. Monitoring Hub (Prometheus, Grafana, Gitea, cAdvisor)
3. Network Alerting (PiAlert)
4. Docker Management (Portainer)
5. Local LLM Agent (Ollama cron worker)
6. Service Dashboard (Heimdall)
7. SIEM Manager (Wazuh)
8. AI Agent (primary — starts once infra is ready)
```

## Boot Order (Node B)

```
1. Network IDS Sensor (Zeek — passive capture, no dependencies)
2. Photo Vault (Immich)
3. File Sync (Nextcloud)
4. Media Stack (heaviest, starts last — 13 containers)
```

## Reference Documents

- **[Security Monitoring](./security-monitoring.md)** — Passive network IDS (Zeek) + Wazuh SIEM architecture, deployment principles, and log reference
