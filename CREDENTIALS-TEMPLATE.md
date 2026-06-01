# Homelab Credential Vault 🔐

> **INTERNAL ONLY** — This doc tracks credentials for local infrastructure.
> **DO NOT** commit to public repositories.
> **Last updated:** $(date +"%B %d, %Y")

---

## 1. Infrastructure Passwords

| System | Host | User | Password |
|--------|------|------|----------|
| Hypervisor | `10.99.99.1` | `root` | `${HYPERVISOR_ROOT_PASSWORD}` |
| Backup Server | `10.99.99.2` | `root` | `${BACKUP_SERVER_ROOT_PASSWORD}` |
| Firewall/Gateway | `10.99.99.1` | `root` | `${FIREWALL_ADMIN_PASSWORD}` |

> **Note:** Firewall is Web UI only — no SSH access configured.

---

## 2. Container (LXC) Root Passwords

| CT ID | Hostname | IP | Password |
|-------|----------|----|----------|
| 100 | management-agent | `10.99.99.100` | SSH key only |
| 101 | service-a | `10.99.99.101` | `${CT_101_ROOT_PASSWORD}` |
| 102 | service-b | `10.99.99.102` | `${CT_102_ROOT_PASSWORD}` |
| ... | ... | ... | ... |

> **SSH access:** All containers accept key-based SSH from the management CT.

---

## 3. Web Service Credentials

| Service | URL | Username | Password / Secret |
|---------|-----|----------|--------------------|
| **Monitoring Dashboard** | http://10.99.99.100:3000 | `admin` | `${GRAFANA_ADMIN_PASSWORD}` |
| **DNS Filter** | http://10.99.99.2/admin | `admin` | `${DNS_FILTER_PASSWORD}` |
| **SIEM Dashboard** | https://10.99.99.101:443 | `admin` | `${SIEM_ADMIN_PASSWORD}` |
| **Uptime Monitor** | http://10.99.99.100:3001 | *(set during setup)* | *(set during setup)* |
| **Git Server** | http://10.99.99.100:3002 | `${GITEA_ADMIN_USER}` | *(set during setup)* |

---

## 4. Enterprise Media Stack — Credentials

### Unified App Password
All services on the media stack use the same admin password:

> **Password:** `${MEDIA_STACK_ADMIN_PASSWORD}`

| Service | Port | URL |
|---------|------|-----|
| **Reverse Proxy (NPM)** | 80 / 81 | http://10.99.99.108:81 |
| **Credential Vault** | 80 (behind NPM) | http://vault.services.internal.lan |
| **Ingress Transport Node** | 8080 | http://10.99.99.108:8080 |
| **Content Aggregator** | 7878 | http://10.99.99.108:7878 |
| **Data Indexer Service** | 8989 | http://10.99.99.108:8989 |
| **Upstream Index Router** | 9696 | http://10.99.99.108:9696 |
| **Data Indexer Service (Audio)** | 8686 | http://10.99.99.108:8686 |
| **Subtitle Enrichment Service** | 6767 | http://10.99.99.108:6767 |
| **Captcha Resolver** | 8191 | http://10.99.99.108:8191 |
| **Internal Streaming Microservice** | 8096 | http://10.99.99.108:8096 |
| **Media Request Gateway** | 5055 | http://10.99.99.108:5055 |

### Reverse Proxy (Default Credentials)
- **URL:** http://10.99.99.108:81
- **Email:** `admin@example.com`
- **Password:** `changeme`
- ⚠️ Change these on first login!

### Credential Vault
- **URL:** http://vault.services.internal.lan (after reverse proxy routing)
- **Admin Panel:** http://vault.services.internal.lan/admin
- **Admin Token:** `${VAULTWARDEN_ADMIN_TOKEN}`
- **Signups:** Disabled after initial account creation

---

## 5. API Tokens & Keys

| System | Token ID | Secret | Purpose |
|--------|----------|--------|---------|
| **Backup Server** | `root@pam!integration` | `${BACKUP_SERVER_API_TOKEN}` | Dashboard integration |
| **Git Server** | `automation-bot` | `${GITEA_AUTOMATION_TOKEN}` | Repo automation |

---

## 6. Boot Order

> All containers on hypervisor

```
1. CT — DNS Filter (DNS first — everything needs DNS)
2. CT — Monitoring Stack (Git, Uptime Monitor, Prometheus, Grafana)
3. CT — Network Alerting
4. CT — Management Agent
5. CT — Photo Vault
6. CT — Dashboard
7. CT — SIEM
8. CT — Office Stack
9. CT — Enterprise Media Stack (starts last, depends on everything else)
```

---

## 7. Network Summary

| Component | IP Address | Notes |
|-----------|------------|-------|
| Firewall/Gateway | 10.99.99.1 | Firewall, DHCP, VLAN routing |
| DNS Filter | 10.99.99.2 | Primary DNS for all LAN |
| Hypervisor Host | 10.99.99.3 | Type-1 hypervisor |
| Backup Server | 10.99.99.4 | Backup server, ZFS mirror pool |
| Management Agent | 10.99.99.100 | AI agent |
| Monitoring Stack | 10.99.99.101 | Monitoring, Git, Uptime Monitor |
| Media Stack | 10.99.99.108 | Content ingestion & streaming |
| SIEM | 10.99.99.110 | Security monitoring |

---

## ⚠️ Critical Notes

1. **Webhook URLs** are NOT stored here — they're in the monitoring stack `.env` file
2. **SSH private keys** are NOT stored here — they live on the management CT
3. **Update this doc** immediately when passwords change
