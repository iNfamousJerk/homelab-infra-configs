# Homelab Infrastructure Configurations

> 🏗️ **Public-ready reference configurations** for a self-hosted homelab stack.

This repository contains sanitized Docker Compose, monitoring, and reverse proxy configurations for a multi-service private infrastructure. All secrets, service names, and identifying details have been replaced with environment variables and generic enterprise terminology.

## Architecture Overview

| Layer | Services | Purpose |
|-------|----------|---------|
| **Hypervisor** | Proxmox VE + PBS | LXC container hosting & ZFS backups |
| **Monitoring** | Prometheus, Grafana, cAdvisor, Blackbox, Uptime Kuma | Metrics, alerting, dashboards |
| **Gateway/Firewall** | OPNsense | VLAN routing, firewall, DHCP |
| **DNS Filter** | Pi-hole | Network-wide ad blocking, local DNS |
| **Source Control** | Gitea | Private git hosting |
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

## Boot Order

```
1. DNS Filter (DNS first — everything needs DNS)
2. Monitoring Stack (Gitea, Uptime Kuma, Prometheus, Grafana)
3. Network Alerting
4. Management Agent
5. Photo Vault
6. Dashboard
7. SIEM
8. Office Stack
9. Media Stack (starts last, depends on everything else)
```
