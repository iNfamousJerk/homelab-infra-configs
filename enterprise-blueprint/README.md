# Automated Data Ingestion Pipeline & Local CDN Architecture

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-24%2B-2496ED?logo=docker)](https://docs.docker.com/compose/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20LXC-lightgrey)]()

> Enterprise-abstracted reference architecture for asynchronous file transfer, metadata enrichment, and local content delivery infrastructure. All recognizable application names have been replaced with generic service descriptors. Zero brand-name leakage. Zero hardcoded secrets.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Service Topology](#service-topology)
- [Networking & Security](#networking--security)
- [Storage Strategy](#storage-strategy)
- [Prerequisites](#prerequisites)
- [Deployment Guide](#deployment-guide)
- [Environment Variables](#environment-variables)
- [Security Considerations](#security-considerations)
- [Operational Notes](#operational-notes)

---

## Architecture Overview

This blueprint defines a **containerized, event-driven data ingestion pipeline** comprising three logical domains:

| Domain | Responsibility | Isolation Level |
|--------|---------------|-----------------|
| **Egress** | Secure outbound tunnel for WAN-bound transfers via encrypted VPN gateway. Includes a P2P transfer node operating within the gateway's network namespace. Kill-switch firewall prevents data egress on tunnel failure. | Fully isolated bridge — only the VPN gateway connects externally |
| **Service** | All processing, indexing, enrichment, orchestration, and delivery services. Internal-only bridge with no external network access. All inter-service communication occurs over a private Docker bridge. | Internal bridge — no WAN access, no host exposure |
| **Ingress** | Reverse proxy (TLS termination, subdomain routing) and credential vault (secrets management). Exposed ports are strictly limited to HTTP/S and admin interface. | Restricted bridge — only proxy and vault |

**Data flow:** `Egress (WAN ingest)` → `Staging Volume` → `Ingestion Engines` → `Curated Volume` → `Local CDN / Enrichment Services` → `Catalog Volume`

---

## Service Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INGRESS NETWORK                              │
│  ┌──────────────────────┐          ┌──────────────────────────────┐ │
│  │   Ingress Controller  │          │      Credential Vault       │ │
│  │   (TLS Termination)   │──────────│   (Secrets Management)      │ │
│  │   :80 :443 :81        │          │   :8082                     │ │
│  └──────────┬───────────┘          └──────────────────────────────┘ │
└─────────────┼───────────────────────────────────────────────────────┘
              │ proxy_pass (subdomain routing)
┌─────────────┼───────────────────────────────────────────────────────┐
│             ▼                   SERVICE NETWORK                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ API Index    │  │  Data        │  │  Data Ingestion          │  │
│  │ Router       │  │  Ingestion   │  │  Engine (Episodic)       │  │
│  │ :9696        │  │  Engine      │  │  :8989                   │  │
│  └──────┬───────┘  │  :7878       │  └──────────────────────────┘  │
│         │          └──────────────┘                                 │
│  ┌──────┴───────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ API Circuit  │  │  Metadata        │  │  Data Ingestion      │  │
│  │ Breaker      │  │  Enrichment      │  │  Engine (Audio)      │  │
│  │ :8191        │  │  :6767           │  │  :8686               │  │
│  └──────────────┘  └──────────────────┘  └──────────────────────┘  │
│  ┌──────────────────┐  ┌───────────────────────────────────────┐   │
│  │  Local CDN       │  │  Content Request Orchestrator        │   │
│  │  :8096           │  │  :5055                               │   │
│  └──────────────────┘  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼───────┐   ┌───────▼───────┐
            │  Staging      │   │  Curated      │
            │  Volume       │   │  Volume       │
            │  (scratch)    │   │  (organized)  │
            └───────────────┘   └───────┬───────┘
                                        │
                                 ┌──────▼──────┐
                                 │  Catalog    │
                                 │  Volume     │
                                 └─────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        EGRESS NETWORK                                │
│  ┌────────────────────────┐       ┌──────────────────────────────┐  │
│  │  Secure Egress Gateway │───┐   │  P2P Transfer Node           │  │
│  │  (VPN Tunnel)          │   │   │  (Shares Gateway Namespace)  │  │
│  │  :8080 :6881           │   └──▶│  Writes to: Staging Volume   │  │
│  └────────────────────────┘       └──────────────────────────────┘  │
│                                                                     │
│  ════════════════════════════════════════════════════════════════    │
│  WAN (Internet)                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Networking & Security

### Microsegmentation Strategy

Three isolated Docker bridge networks enforce least-privilege communication:

| Network | CIDR | External Access | Members |
|---------|------|-----------------|---------|
| `egress_network` | `172.20.0.0/24` | ✅ WAN (via VPN) | VPN gateway, P2P node |
| `service_network` | `172.20.1.0/24` | ❌ None | All processing services |
| `ingress_network` | `172.20.2.0/24` | ⚠️ Port 80/443/81 | Reverse proxy, credential vault |

### Key Security Properties

- **Default-deny egress:** The `service_network` bridge is created with `internal: true`. Services on this network reach neither the internet nor the host's external interfaces. Any compromise of a service in this segment cannot be used to exfiltrate data.
- **VPN kill switch:** The egress gateway enforces `IPTABLES` firewall rules that block all non-tunnel traffic. If the VPN tunnel drops, the P2P transfer node (sharing the gateway's namespace) has zero network connectivity — no data leakage.
- **DMZ ingress:** Only the reverse proxy exposes ports to the LAN. All upstream services are reachable exclusively via proxy_pass, never via direct port exposure.
- **TLS termination:** The ingress controller terminates TLS at the edge. Backend traffic between the proxy and services uses plaintext Docker DNS, keeping certificate management centralized.

### DNS Architecture

- Internal service discovery uses Docker embedded DNS (service hostnames resolve automatically within compose-defined networks).
- External DNS resolution for the egress gateway is explicitly set to `${DNS_PRIMARY:-1.1.1.1}` to bypass local DNS filters during WAN transfers.
- LAN-facing DNS for *.internal.lan subdomains should be configured on the network's authoritative DNS server (e.g., Pi-hole, Bind9, CoreDNS).

---

## Storage Strategy

### Volume Lifecycle Management

| Volume | Mount Point | Backing Store | IO Profile | Durability Class |
|--------|-------------|---------------|------------|------------------|
| `staging_data` | `/mnt/data/pipeline/staging` | NVMe / SSD scratch | High-write, transient | Ephemeral — loss tolerable |
| `curated_data` | `/mnt/data/pipeline/curated` | SSD or mirror | Moderate-write, indexed | Persistent — RAID-1 recommended |
| `catalog_data` | `/mnt/data/pipeline/catalog` | HDD array / ZFS pool | Read-heavy, append-only | Persistent — RAID-6 or ZFS RAIDZ2 |

### Design Rationale

1. **Scratch-disk isolation:** The staging volume mounts a dedicated SSD or NVMe device. This absorbs the high write-amplification from P2P transfer writes, preventing SSD wear-out on the curated and catalog volumes. This volume has no redundancy requirement — loss of in-flight data is acceptable.

2. **ZFS / RAID abstraction:** The curated and catalog volumes should ideally back onto a ZFS pool or hardware RAID array. ZFS provides:
   - **Checksumming:** Silent data corruption detection during reads
   - **Compression:** lz4 or zstd compression for catalog metadata
   - **Snapshots:** Point-in-time recovery for curation errors
   - **Scrubbing:** Periodic data integrity verification

3. **Transcode cache isolation:** The CDN service's transcode cache is mapped to a separate path (`${TRANSCODE_CACHE}`) outside the main volumes. Transcode artifacts are regeneratable and should be stored on fast ephemeral storage.

---

## Prerequisites

- **Docker Engine** 24.0+ with Compose v2 plugin
- **Linux kernel** 5.x+ (for `apparmor=unconfined` security profiles)
- **TUN device** (for VPN gateway):
  ```bash
  # Bare metal / VM
  sudo modprobe tun

  # LXC container (add to container config on hypervisor)
  lxc.cgroup2.devices.allow: c 10:200 rwm
  lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
  ```
- **Storage** — At minimum 50GB for staging, 500GB+ recommended for curated/catalog volumes
- **DNS** — Wildcard `*.internal.lan` A record pointing to the host's LAN IP (for subdomain-based service access)

---

## Deployment Guide

### 1. Clone & Configure

```bash
git clone <repository-url> data-pipeline
cd data-pipeline

# Create environment file from template
cp .env.example .env

# Edit .env with your values
# Minimum required: VPN credentials, VAULT_ADMIN_TOKEN, storage paths
vim .env
```

### 2. Deploy the Stack

```bash
# Start all services
docker compose up -d

# Monitor bootstrap
docker compose logs --tail=50 -f

# Verify all services are healthy
docker compose ps
```

### 3. Post-Deployment Configuration

1. **Ingress Controller:** Navigate to `http://<host-ip>:81` and complete initial setup (default credentials: `admin@example.com` / `changeme`).
2. **Credential Vault:** Access via the ingress controller at `https://vault.internal.lan/admin` using the `${VAULT_ADMIN_TOKEN}` set in `.env`.
3. **Service Configuration:** Each web UI is accessible at `http://<service-name>.internal.lan` after configuring proxy hosts in the ingress controller.

### 4. Scaling & Maintenance

```bash
# Update all images
docker compose pull
docker compose up -d

# View resource usage
docker stats

# Backup configuration volumes
tar czf backup-$(date +%Y%m%d).tar.gz \
  ./config/ \
  -C /var/lib/docker/volumes/ \
  $(docker volume ls --filter name=data-pipeline --format '{{.Name}}' | grep -v staging)
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPOSE_PROJECT_NAME` | `data-pipeline` | Docker Compose project namespace |
| `PUID` / `PGID` | `1000` | User/group ID for file ownership |
| `TZ` | `America/New_York` | Container timezone |
| `STAGING_PATH` | `/mnt/data/pipeline/staging` | Scratch disk mount for in-transit payloads |
| `CURATED_PATH` | `/mnt/data/pipeline/curated` | Organized asset store |
| `CATALOG_PATH` | `/mnt/data/pipeline/catalog` | Final content catalog |
| `TRANSCODE_CACHE` | `/mnt/data/pipeline/transcode` | CDN transcode working directory |
| `VPN_SERVICE_PROVIDER` | *(empty)* | VPN provider name (leave empty to skip VPN) |
| `VPN_USER` | — | VPN authentication username |
| `VPN_PASSWORD` | — | VPN authentication password |
| `VPN_FIREWALL` | `on` | Enable kill-switch firewall |
| `VAULT_ADMIN_TOKEN` | — | Credential vault administrative token |
| `DNS_PRIMARY` | `1.1.1.1` | Upstream DNS resolver for egress |

See `.env.example` for the complete variable reference.

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| **Credential exposure** | All secrets via `.env` (`.gitignore`'d). Vaultwarden manages runtime credentials. Pre-commit hook scans staged files for secret patterns. |
| **Egress data leakage** | Service network is `internal: true`. VPN gateway enforces iptables kill switch. P2P node shares gateway namespace — no independent network access. |
| **Container breakout** | `apparmor=unconfined` is set only on ingestion and enrichment services that require filesystem access. All other profiles should be hardened. |
| **Supply chain** | Images pinned to `latest` for simplicity. For production, pin to specific digests or use a private registry mirror. |
| **Logging** | Logs contain service names and query metadata. Ensure log shipping destinations (if any) are access-controlled. |

---

## Operational Notes

- **Restart policy:** All services use `unless-stopped`. Manual `docker stop` will persist the stopped state across host reboots; use `docker compose down` for intentional teardown.
- **VPN recovery:** If the VPN gateway restarts, the P2P node (sharing its namespace) will also restart after the gateway reports healthy. This is automatic and requires no operator intervention.
- **Storage monitoring:** Set up disk usage alerts on all three pipeline volumes. The staging volume is particularly write-intensive and may fill faster than expected during heavy transfer periods.
- **Backup strategy:** Configuration volumes (named volumes without bind mounts) should be backed up regularly. Staging volume data is transient and does not require backup. Curated and catalog volumes should be on RAID/ZFS with regular snapshot schedules.

---

## License

MIT — This is a reference architecture blueprint. Use, modify, and adapt freely.
