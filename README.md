# Homelab Infrastructure Configurations

> 🏗️ **Public-ready reference configurations** for a self-hosted homelab stack.

This repository contains sanitized Docker Compose, monitoring, and reverse proxy configurations for a multi-service private infrastructure. All secrets, service names, and identifying details have been replaced with environment variables and generic enterprise terminology.

## Architecture Overview

| Layer | Services | Purpose |
|-------|----------|---------|
| **Hypervisor** | Proxmox VE (×2 nodes) + PBS | Dual-node LXC container hosting, ZFS-backed backups |
|| **PVE1** — `10.2.7.x` | i7-9700, 64GB, LVM-thin | Legacy node — remaining non-migrated LXCs |
|| **PVE2** — `10.2.7.x` | i7-2600K, 16GB, 128GB SSD boot, ZFS pool (2.72TB) | Primary storage node — ZFS for media, photos, files |
|| **ZFS Pool** `media` | Mirror-0: 2TB HGST + 2TB Toshiba ; Mirror-1: 1TB Seagate + 1TB Hitachi | Checksummed, portable storage for all bulk data |
|| **Monitoring** | Prometheus, Grafana, cAdvisor, Blackbox, Uptime Kuma | Metrics, alerting, dashboards |
|| **Backup** | Proxmox Backup Server | Snapshot-based LXC/VM backups (Zstd compression) |
| **Gateway/Firewall** | OPNsense | VLAN routing, firewall, DHCP |
| **DNS Filter** | Pi-hole | Network-wide ad blocking, local DNS |
| **Monitoring** | Prometheus, Grafana, cAdvisor, Blackbox, Uptime Kuma | Metrics, alerting, dashboards |
| **Identity & Helpdesk** | Keycloak SSO, Snipe-IT, osTicket | SSO, asset management, helpdesk |
| **Source Control** | Gitea | Private git hosting |
| **Photo Vault** | Immich (bare-metal) | Self-hosted Google Photos alternative, PostgreSQL + pgvector |
| **File Sync** | Nextcloud (TurnKey) | Self-hosted file sync & share, Apache + MariaDB + Redis |
| **Automation Agent** | Hermes (primary) | AI orchestration, cron jobs, Discord gateway |
| **Media Stack** | See below | Content ingestion, indexing, streaming |
| **Credential Vault** | Vaultwarden (in media stack) | Self-hosted password management |

## Media Stack — Enterprise Abstraction Reference

| Generic Name | Actual Software | Purpose | Port |
|-------------|----------------|---------|------|
| `vpn-gateway` | Gluetun | VPN tunnel (OpenVPN/WireGuard) | — |
| `ingress-transport-node` | qBittorrent | Torrent download client | 8080 |
| `upstream-index-router` | Prowlarr | Indexer aggregation & searching | 9696 |
| `content-aggregator` | Radarr | Film/feature content automation | 7878 |
| `data-indexer-service` | Sonarr | Episodic content automation | 8989 |
| `data-indexer-service-2` | Lidarr | Audio content automation | 8686 |
| `subtitle-enrichment-service` | Bazarr | Subtitle acquisition & management | 6767 |
| `internal-streaming-microservice` | Jellyfin | Media streaming server | 8096 |
| `media-request-gateway` | Seerr (Jellyseerr) | Media request management & discovery | 5055 |
| `audiobook-ebook-server` | Audiobookshelf | Audiobook & ebook streaming | 13378 |
| `captcha-resolver` | FlareSolverr | Cloudflare challenge bypass | 8191 |
| `credential-vault` | Vaultwarden | Password management | — |
| `reverse-proxy` | Nginx Proxy Manager | SSL termination & domain routing | 80/443/81 |
| `manga-request` | Manga Request | Manga acquisition requests | 5000 |

## Infrastructure Layout

| Host | Type | Hardware | Containers |
|------|------|----------|------------|
| **Node A** (PVE 9.x) | Hypervisor | i5-7500, 32GB RAM, 1TB SSD | AI agent, DNS, monitoring hub, identity, file/photo storage |
| **Node B** (PVE 8.x) | Hypervisor | i7-2600K, 16GB RAM, 3.62TB ZFS pool | Media stack, ripping, transcoding/optimization |

## Active Container Reference

| Role | Host | OS | Cores | RAM | Disk | Purpose |
|------|------|-----|-------|-----|------|---------|
| **AI Agent (primary)** | Node A | Debian 13 | 2 | 4GB | 20GB | Main automation agent, Discord gateway, cron orchestration |
| **Monitoring Hub** | Node A | Debian 13 | 2 | 4GB | 30GB | Grafana, Prometheus, Alertmanager, Gitea, Uptime Kuma, exporters — 11 Docker services |
| **DNS Filter** | Node A | Debian 13 | 2 | 4GB | 4GB | Pi-hole network DNS & ad blocking |
| **Photo Vault** | Node A | Debian 13 | 2 | 4GB | 14GB | Immich photo management (bare-metal source build) |
| **File Sync** | Node A | Debian 12 | 2 | 2GB | 8GB | Nextcloud file sync & share (TurnKey) |
| **Identity (SSO)** | Node A | Debian 13 | 1 | 2GB | 10GB | Keycloak — centralized OpenID Connect / SAML identity provider |
| **Asset Management** | Node A | Debian 13 | 1 | 2GB | 10GB | Snipe-IT — IT asset / license tracking (Docker) |
| **Helpdesk** | Node A | Debian 13 | 1 | 2GB | 10GB | osTicket — ticketing / helpdesk system (Docker) |
| **Service Dashboard** | Node A | Debian 13 | 1 | 1GB | 10GB | Arr Dashboard — unified media-stack UI (Docker) |
| **Book/Manga Automation** | Node A | Debian 13 | 2 | 2GB | 50GB | Librarr book/audiobook/manga search + download |
| **Manga Reader** | Node A | Debian 13 | 2 | 2GB | 20GB | Komga — manga/comic reader (bare-metal jar) |
| **Media Stack** | Node B | Debian 13 | 4 | 4GB | 40GB + ZFS | 16 Docker containers — VPN-protected media pipeline (Gluetun, qBittorrent, Jellyfin, *arrs, NPM, Vaultwarden) |
| **Ripping Station** | Node B | Debian 13 | 2 | 2GB | 8GB | DVD/Blu-ray ripping with Flask web UIs |
| **Media Optimizer** | Node B | Debian 13 | 4 | 4GB | 30GB | Tdarr — audio-track trimming + x265 re-encode batch (currently paused) |

> **14 total containers.** 11 on Node A, 3 on Node B.
> **Past deployments (retired 2026-08):** Wazuh SIEM manager, Zeek passive network IDS sensor, Portainer, Heimdall dashboard, PiAlert ARP discovery, local-LLM agent CT, Cockpit, Donetick, cheatsheet. SIEM/IDS functionality consolidated into the monitoring hub; container management via Portainer Agent endpoints.

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
├── MIGRATION-GUIDE.md              # Step-by-step PVE1→PVE2 migration docs
├── nginx-default.conf              # Nginx reverse proxy subdomain config
├── nginx.conf                      # Base nginx configuration
├── prometheus.yml                  # Prometheus scrape configuration
├── alertmanager.yml                # Alertmanager routing & receivers
├── homelab_alerts.yml              # Prometheus alerting rules
├── .env.example                    # Environment variable template
├── CREDENTIALS-TEMPLATE.md         # Credential tracking template (NEVER commit real creds)
└── scripts/
    ├── pre-commit-secret-scan.py   # Pre-commit hook for secret detection
    └── check-pve-pbs-updates.sh    # Multi-node health check (PVE×2 + PBS)
```

## Security

- **All secrets** are injected via `.env` files — never hardcoded
- **VPN kill switch** prevents IP leaks on VPN drop
- **Pre-commit hook** scans staged files for API keys, tokens, and credentials
- **`.gitignore`** blocks `.env`, `.pem`, `.key`, `config/` directories, and more
- **RFC1918 private IPs** only — no public WAN addresses exposed

## Boot Order (Node A)

```
1. DNS Filter (Pi-hole — must boot first)
2. Monitoring / Identity Hub (Grafana, Keycloak, Gitea, etc.)
3. AI Agent (Hermes)
4. Photo Vault (Immich)
5. File Sync (Nextcloud)
6. Book/Manga Automation (Librarr)
```

## Boot Order (Node B)

```
1. Media Stack (heaviest, starts first — 19 containers)
2. Ripping Station
3. Media Optimizer (Tdarr — starts last, after media is up)
```

## Reference Documents

- **[Security Monitoring](./security-monitoring.md)** — Passive network IDS (Zeek) + Wazuh SIEM architecture (deployment retired 2026-08; kept as reference)
- **[Client Portal + GPU Streaming](./client-portal-reference.md)** — Sanitized multi-tenant client portal reference: tenant-per-container isolation, all-VPN access (zero public exposure), GPU-accelerated transcoding, SSO per client
