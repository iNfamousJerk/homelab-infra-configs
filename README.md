# Homelab Infrastructure Configurations

> 🏗️ **Public-ready reference configurations** for a self-hosted homelab stack.

This repository contains sanitized Docker Compose, monitoring, and reverse proxy configurations for a multi-service private infrastructure. All secrets, service names, and identifying details have been replaced with environment variables and generic enterprise terminology.

## Architecture Overview

| Layer | Services | Purpose |
|-------|----------|---------|
| **Hypervisor** | Proxmox VE (×2 nodes) + PBS | Dual-node LXC container hosting, ZFS-backed backups |
|| **Node A** — `10.2.7.x` | i5-7500, 32GB, 1TB SSD | Primary application node — identity, monitoring, storage apps, media automation/server (19 LXCs) |
|| **Node B** — `10.2.7.x` | i7-2600K, 32GB, ZFS pool (3.62TB) | Storage + media-download node — ZFS for media, photos, files (3 LXCs) |
|| **ZFS Pool** `media` | 3.62T total, 2.48T used | Checksummed, portable storage for all bulk data |
|| **Monitoring** | Prometheus, Grafana, cAdvisor, Blackbox, Alertmanager, Uptime Kuma | Metrics, alerting, dashboards |
|| **SIEM** | Wazuh (Docker) | Centralized security event monitoring, log ingestion, FIM, vulnerability scanning (resurrected 2026-08) |
|| **Security Workbench** | Parrot OS (Xfce) | Dedicated security-testing desktop — pen-test toolset (offensive counterpart to the SIEM) |
|| **Backup** | Proxmox Backup Server | Snapshot-based LXC/VM backups (Zstd compression) |
| **Gateway/Firewall** | OPNsense | VLAN routing, firewall, DHCP |
| **DNS Filter** | Pi-hole | Network-wide ad blocking, local DNS |
| **Identity & Helpdesk** | Keycloak SSO, Snipe-IT, osTicket | SSO, asset management, helpdesk |
| **Source Control** | Gitea | Private git hosting |
| **Photo Vault** | Immich | Self-hosted Google Photos alternative, PostgreSQL + pgvector |
| **File Sync** | Nextcloud (TurnKey) | Self-hosted file sync & share, Apache + MariaDB + Redis |
| **Document Management** | Paperless-ngx | Self-hosted document archiving & OCR |
| **Automation Agent** | Hermes (primary) | AI orchestration, cron jobs, Discord gateway |
| **Credential Vault** | Vaultwarden | Self-hosted password management |
| **Reverse Proxy** | Nginx Proxy Manager | SSL termination & domain routing |

## Node A (Application) — 21 Containers

| CT ID | Role | OS | Cores | RAM | Purpose |
|-------|------|-----|-------|-----|---------|
| 100 | **AI Agent (primary)** | Debian 13 | 2 | 4GB | Main automation agent, Discord gateway, cron orchestration |
| 101 | **Service Dashboard** | Debian 13 | 2 | 1GB | Homarr — unified dashboard UI |
| 105 | **SIEM** | Debian 13 | 4 | 8GB | Wazuh (Docker single-node) — security event monitoring, log ingestion, FIM, vulnerability scanning (resurrected 2026-08) |
| 106 | **Monitoring Hub** | Ubuntu 24.04 | 2 | 4GB | Grafana, Prometheus, Alertmanager, Uptime Kuma, exporters (10 Docker services) |
| 107 | **DNS Filter** | Debian 13 | 2 | 4GB | Pi-hole network DNS & ad blocking |
| 111 | **Photo Vault** | Debian 13 | 2 | 4GB | Immich photo management |
| 112 | **File Sync** | Debian 13 | 2 | 2GB | Nextcloud file sync & share (TurnKey) |
| 116 | **Media Automation** | Debian 13 | 4 | 4GB | *Arr stack + Librarr: indexer, download automation, book/manga search (8 Docker services) |
| 117 | **Media Server** | Debian 13 | 4 | 4GB | Jellyfin streaming + Seerr media requests |
| 120 | **Identity (SSO)** | Debian 13 | 2 | 2GB | Keycloak — centralized OpenID Connect / SAML identity provider |
| 121 | **Asset Management** | Debian 13 | 2 | 2GB | Snipe-IT — IT asset / license tracking |
| 122 | **Helpdesk** | Debian 13 | 2 | 2GB | osTicket — ticketing / helpdesk |
| 123 | **Arr Dashboard** | Debian 13 | 2 | 4GB | Unified media-stack UI |
| 125 | **Source Control** | Ubuntu 24.04 | 2 | 2GB | Gitea — private git hosting |
| 130 | **Manga Reader** | Ubuntu 24.04 | 2 | 2GB | Komga — manga/comic reader (bare-metal jar) |
| 140 | **Database** | Debian 13 | 2 | 2GB | PostgreSQL — supports Keycloak & co |
| 141 | **Document Mgmt** | Debian 13 | 2 | 2GB | Paperless-ngx — document archiving & OCR |
| 142 | **Low-code DB** | Debian 13 | 1 | 1GB | NocoDB — spreadsheet-style database app |
| 143 | **Credential Vault** | Debian 13 | 2 | 1GB | Vaultwarden — password management |
| 144 | **Reverse Proxy** | Debian 13 | 2 | 1GB | Nginx Proxy Manager — SSL & domain routing |
| 145 | **Security Workbench** | Debian 13 (Parrot) | 4 | 4GB | Parrot OS Security Edition — Xfce desktop, pen-test toolset (nmap, metasploit, hashcat, burpsuite). Privileged CT (TUN/TAP for VPN testing) |

## Node B (Storage & Media Download) — 3 Containers

| CT ID | Role | OS | Cores | RAM | Purpose |
|-------|------|-----|-------|-----|---------|
| 103 | **Ripping Station** | Debian 13 | 2 | 2GB | DVD/Blu-ray ripping with Flask web UIs |
| 110 | **Media Ingress/Sync** | Debian 13 | 4 | 4GB | VPN gateway (Gluetun), download client (qBittorrent), Audiobookshelf, Navidrome |
| 118 | **Media Optimizer** | Debian 13 | 4 | 6GB | Tdarr — audio-track trimming + x265 re-encode batch (currently paused) |

> **24 total containers.** 21 on Node A, 3 on Node B.
> **Retired 2026-08:** Zeek passive network IDS sensor, Portainer, Heimdall dashboard, PiAlert ARP discovery, local-LLM agent CT, Cockpit, Donetick, cheatsheet. **Wazuh SIEM** was retired 2026-08 but **resurrected 2026-08-30** as a Docker single-node stack (CT 105) + **Parrot OS** security workbench added (CT 145) — the security/IDS capability now lives in these two dedicated CTs (plus syslog ingestion from the firewall into Wazuh). Windows AD lab (VMs) decommissioned 2026-08-30 in favor of the SIEM + offensive-security pivot.

## Media Stack — Enterprise Abstraction Reference

The media pipeline is **distributed across Node A and Node B** (ingress stays behind the VPN on the storage node; automation, streaming, and requests live on the application node).

| Layer | Generic Name | Actual Software | Node | CT |
|-------|-------------|-----------------|------|----|
| **Automation & Indexing** | `upstream-index-router` | Prowlarr | Node A | 116 |
| | `content-aggregator` | Radarr | Node A | 116 |
| | `data-indexer-service` | Sonarr | Node A | 116 |
| | `data-indexer-service-2` | Lidarr | Node A | 116 |
| | `subtitle-enrichment-service` | Bazarr | Node A | 116 |
| | `media-request-gateway` | Seerr | Node A | 117 |
| | `book/manga-automation` | Librarr | Node A | 116 |
| **Streaming** | `internal-streaming-microservice` | Jellyfin | Node A | 117 |
| **VPN + Download** | `vpn-gateway` | Gluetun | Node B | 110 |
| | `ingress-transport-node` | qBittorrent | Node B | 110 |
| **Books & Music** | `audiobook-ebook-server` | Audiobookshelf | Node B | 110 |
| | `audio-server` | Navidrome | Node B | 110 |
| **Infra** | `captcha-resolver` | FlareSolverr | Node A | 116 |
| | `reverse-proxy` | Nginx Proxy Manager | Node A | 144 |
| | `credential-vault` | Vaultwarden | Node A | 143 |

## Infrastructure Layout

| Host | Type | Hardware | Role |
|------|------|----------|------|
| **Node A** (PVE 9.x) | Hypervisor | i5-7500, 32GB RAM, 1TB SSD | 21 LXCs — application node (AI, DNS, monitoring, SIEM, security, storage apps, media automation/server) |
| **Node B** (PVE 6.x) | Hypervisor | i7-2600K, 32GB RAM, 3.62TB ZFS pool | 3 LXCs — storage + media download/ingress |
| **Backup** | PBS | ZFS datastore | Nightly LXC/VM snapshots |

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Linux (tested on Debian 12/13 LXC containers)
- A VPN subscription (for the media ingress node)
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

> **Note:** The `docker-compose.yml` / `media-stack.yml` files here are sanitized *reference examples*. The live deployment is managed per-container via tracked compose stacks in private source control.

## File Layout

```
.
├── docker-compose.yml              # Monitoring stack (Prometheus, Grafana, etc.)
├── media-stack.yml                 # Media stack — production (VPN-protected)
├── nextcloud-office-stack.yml      # Office productivity stack
├── enterprise-blueprint/           # Larger-enterprise reference architecture
├── MIGRATION-GUIDE.md              # Step-by-step PVE1→PVE2 migration docs
├── nginx-default.conf              # Nginx reverse proxy subdomain config
├── nginx.conf                      # Base nginx configuration
├── prometheus.yml                  # Prometheus scrape configuration
├── alertmanager.yml                # Alertmanager routing & receivers
├── homelab_alerts.yml              # Prometheus alerting rules
├── .env.example                    # Environment variable template
├── CREDENTIALS-TEMPLATE.md         # Credential tracking template (NEVER commit real creds)
├── security-monitoring.md          # Retired SIEM/IDS reference architecture
├── client-portal-reference.md      # Sanitized multi-tenant client portal reference
├── training/                       # Beginner training manuals per service
└── scripts/
    ├── pre-commit-secret-scan.py   # Pre-commit hook for secret detection
    ├── check-pve-pbs-updates.sh    # Multi-node health check (PVE×2 + PBS)
    └── ...                         # Deployment / utility scripts
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
2. Reverse Proxy (NPM) + Monitoring / Identity Hub (Keycloak, Gitea, etc.)
3. Database (PostgreSQL) + Credential Vault (Vaultwarden)
4. AI Agent (Hermes)
5. Photo Vault (Immich)
6. File Sync (Nextcloud)
7. Media Automation (Librarr + *arr) and Media Server (Jellyfin)
```

## Boot Order (Node B)

```
1. Media Ingress (VPN gateway + download client — heaviest, starts first)
2. Ripping Station
3. Media Optimizer (Tdarr — starts last, after media is up)
```

## Reference Documents

- **[Security Monitoring](./security-monitoring.md)** — SIEM (Wazuh, **live**) + passive network IDS (Zeek, planned) reference architecture
- **[Client Portal + GPU Streaming](./client-portal-reference.md)** — Sanitized multi-tenant client portal reference: tenant-per-container isolation, all-VPN access (zero public exposure), GPU-accelerated transcoding, SSO per client
- **[Enterprise Blueprint](./enterprise-blueprint/README.md)** — Abstracted larger-scale reference architecture (content pipeline, catalog storage, egress/ingress networking)
