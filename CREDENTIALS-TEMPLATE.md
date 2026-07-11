# Homelab Credential Vault 🔐

> **INTERNAL ONLY** — This doc tracks credentials for local infrastructure.
> **DO NOT** commit to public repositories.
> **Last updated:** July 10, 2026

---

## 1. Infrastructure Passwords

| System | Host | User | Password |
|--------|------|------|----------|
| Hypervisor (Node A) | `10.x.x.1` | `root` | `${HYPERVISOR_A_ROOT_PASSWORD}` |
| Hypervisor (Node B) | `10.x.x.2` | `root` | `${HYPERVISOR_B_ROOT_PASSWORD}` |
| Backup Server (PBS) | `10.x.x.3` | `root` | `${BACKUP_SERVER_ROOT_PASSWORD}` |
| Firewall/Gateway (OPNsense) | `10.x.x.4` | `root` | `${FIREWALL_ADMIN_PASSWORD}` |

> **Note:** Firewall is Web UI only — no SSH access configured.

---

## 2. Container (LXC) Root Passwords

| CT ID | Hostname | IP | Password |
|-------|----------|----|----------|
| 100 | hermesagent | `10.x.x.100` | SSH key only |
| 101 | zeek | `10.x.x.101` | `${CT_101_ROOT_PASSWORD}` |
| 102 | pialert | `10.x.x.102` | `${CT_102_ROOT_PASSWORD}` |
| 103 | ripper | `10.x.x.103` | `${CT_103_ROOT_PASSWORD}` |
| 104 | micromd | `10.x.x.104` | `${CT_104_ROOT_PASSWORD}` |
| 105 | wazuh | `10.x.x.105` | `${CT_105_ROOT_PASSWORD}` |
| 106 | grafana | `10.x.x.106` | `${CT_106_ROOT_PASSWORD}` |
| 107 | pihole | `10.x.x.107` | `${CT_107_ROOT_PASSWORD}` |
| 108 | portainer | `10.x.x.108` | `${CT_108_ROOT_PASSWORD}` |
| 109 | heimdall-dashboard | `10.x.x.109` | `${CT_109_ROOT_PASSWORD}` |
| 110 | media-stack | `10.x.x.110` | `${CT_110_ROOT_PASSWORD}` |
| 111 | immich | `10.x.x.111` | `${CT_111_ROOT_PASSWORD}` |
| 112 | nextcloud | `10.x.x.112` | `${CT_112_ROOT_PASSWORD}` |
| 113 | hermes-ollama | `10.x.x.113` | `${CT_113_ROOT_PASSWORD}` |
| 114 | cockpit | `10.x.x.114` | `${CT_114_ROOT_PASSWORD}` |

> **SSH access:** All containers accept key-based SSH from the management CT.

---

## 3. Windows Virtual Machine Credentials

| VM ID | Role | Hostname | OS | IP | Username | Password |
|-------|------|----------|----|----|----------|----------|
| 200 | Domain Controller | dc-2025 | Windows Server 2025 | `10.x.x.200` | `Administrator` | `${DC_ADMIN_PASSWORD}` |
| 201 | Domain Client | win-client | Windows 11 | `10.x.x.201` | `.\\Administrator` | `${WIN_CLIENT_ADMIN_PASSWORD}` |

### Active Directory Lab

| Component | Value |
|-----------|-------|
| Domain | `homelab.local` |
| Domain Admin | `HOMELAB\\Administrator` |
| Domain Admin Password | `${DOMAIN_ADMIN_PASSWORD}` |
| Organizational Units | `Employees → IT`, `Computers`, `Groups` |
| Remote Management | WinRM (HTTP on 5985, HTTPS on 5986) |

---

## 4. Web Service Credentials

| Service | URL | Username | Password / Secret |
|---------|-----|----------|--------------------|
| **Monitoring Dashboard (Grafana)** | http://10.x.x.x:3000 | `admin` | `${GRAFANA_ADMIN_PASSWORD}` |
| **DNS Filter (Pi-hole)** | http://10.x.x.x/admin | `admin` | `${DNS_FILTER_PASSWORD}` |
| **SIEM Dashboard (Wazuh)** | https://10.x.x.x:443 | `admin` | `${SIEM_ADMIN_PASSWORD}` |
| **Uptime Monitor (Kuma)** | http://10.x.x.x:3001 | *(set during setup)* | *(set during setup)* |
| **Git Server (Gitea)** | http://10.x.x.x:3002 | `${GITEA_ADMIN_USER}` | *(set during setup)* |
| **IT Asset Management (Snipe-IT)** | http://10.x.x.x:8000 | `admin` | `${SNIPEIT_ADMIN_PASSWORD}` |
| **MDM Server (MicroMDM)** | https://10.x.x.x:8443 | *(API key)* | `${MICROMD_API_KEY}` |
| **Patch Monitoring (PatchMon)** | http://10.x.x.x:3000 | *(via Wazuh)* | *(set during setup)* |
| **Container Management (Portainer)** | http://10.x.x.x:9000 | `admin` | `${PORTAINER_ADMIN_PASSWORD}` |
| **Service Dashboard (Heimdall)** | http://10.x.x.x | *(set during setup)* | *(set during setup)* |
| **Photo Management (Immich)** | http://10.x.x.x:2283 | *(set during setup)* | *(set during setup)* |
| **File Sync (Nextcloud)** | http://10.x.x.x | `admin` | `${NEXTCLOUD_ADMIN_PASSWORD}` |
| **AI Agent (Hermes)** | http://10.x.x.x:8080 | *(API key)* | `${HERMES_API_KEY}` |

### Cockpit Dashboards

Cockpit is installed on most containers for centralized management. Access via port 9090.

| CT ID | Hostname | Cockpit URL |
|-------|----------|-------------|
| 100 | hermesagent | https://10.x.x.x:9090 |
| 102 | pialert | https://10.x.x.x:9090 |
| 105 | wazuh | https://10.x.x.x:9090 |
| 106 | grafana | https://10.x.x.x:9090 |
| 107 | pihole | https://10.x.x.x:9090 |
| 111 | immich | https://10.x.x.x:9090 |
| 112 | nextcloud | https://10.x.x.x:9090 |
| 113 | hermes-ollama | https://10.x.x.x:9090 |
| 114 | cockpit | https://10.x.x.x:9090 |

> **Default Cockpit credentials:** Local Unix user or root password for each CT.

---

## 5. Enterprise Media Stack — Credentials

### Unified App Password
All services on the media stack use the same admin password:

> **Password:** `${MEDIA_STACK_ADMIN_PASSWORD}`

| Service | Port | URL |
|---------|------|-----|
| **Reverse Proxy (NPM)** | 80 / 81 | http://10.x.x.x:81 |
| **Credential Vault** | 80 (behind NPM) | http://vault.services.internal.lan |
| **Ingress Transport Node** | 8080 | http://10.x.x.x:8080 |
| **Content Aggregator** | 7878 | http://10.x.x.x:7878 |
| **Data Indexer Service** | 8989 | http://10.x.x.x:8989 |
| **Upstream Index Router** | 9696 | http://10.x.x.x:9696 |
| **Data Indexer Service (Audio)** | 8686 | http://10.x.x.x:8686 |
| **Subtitle Enrichment Service** | 6767 | http://10.x.x.x:6767 |
| **Captcha Resolver** | 8191 | http://10.x.x.x:8191 |
| **Internal Streaming Microservice** | 8096 | http://10.x.x.x:8096 |
| **Media Request Gateway** | 5055 | http://10.x.x.x:5055 |

### Reverse Proxy (Default Credentials)
- **URL:** http://10.x.x.x:81
- **Email:** `admin@example.com`
- **Password:** `changeme`
- ⚠️ Change these on first login!

### Credential Vault
- **URL:** http://vault.services.internal.lan (after reverse proxy routing)
- **Admin Panel:** http://vault.services.internal.lan/admin
- **Admin Token:** `${VAULTWARDEN_ADMIN_TOKEN}`
- **Signups:** Disabled after initial account creation

---

## 6. API Tokens & Keys

| System | Token ID | Secret | Purpose |
|--------|----------|--------|---------|
| Backup Server (PBS) | `root@pam!integration` | `${BACKUP_SERVER_API_TOKEN}` | Dashboard integration |
| Git Server (Gitea) | `automation-bot` | `${GITEA_AUTOMATION_TOKEN}` | Repo automation |
| MDM (MicroMDM) | `api` | `${MICROMD_API_KEY}` | Apple device enrollment API |
| AI Agent (Hermes) | `hermes-api` | `${HERMES_API_KEY}` | External API access |

---

## 7. Boot Order

### Node A

```
 1. CT 107 — DNS Filter (Pi-hole) — DNS first — everything needs DNS
 2. CT 106 — Monitoring Hub (Grafana, Prometheus, Gitea, Uptime Kuma)
 3. CT 102 — Network Alerting (PiAlert)
 4. CT 108 — Container Management (Portainer)
 5. CT 113 — Local LLM Inference (Ollama)
 6. CT 109 — Service Dashboard (Heimdall)
 7. CT 105 — SIEM Manager (Wazuh)
 8. CT 100 — AI Orchestration Agent (Hermes)
 9. CT 114 — Centralized Management (Cockpit)
```

### Node B

```
 1. CT 101 — Network IDS Sensor (Zeek) — passive, no dependencies
 2. CT 111 — Photo Management (Immich)
 3. CT 112 — File Sync & Share (Nextcloud)
 4. CT 104 — MDM Server (MicroMDM)
 5. CT 110 — Media Stack Host (18 containers, starts last)
 6. CT 103 — Media Automation (DVD ripping)
```

---

## 8. Network Summary

| Component | IP Address | Host | Notes |
|-----------|------------|------|-------|
| OPNsense Gateway/Firewall | 10.x.x.1 | Physical | Firewall, DHCP, VLAN routing, Tailscale subnet router |
| Proxmox Node A | 10.x.x.2 | Physical | HP ProDesk 400 G4, i5-7500, 32GB |
| Proxmox Node B | 10.x.x.3 | Physical | Custom build, i7-2600K, 16GB |
| Proxmox Backup Server | 10.x.x.4 | Physical | HP Z230, Xeon E3-1225 v3, 16GB |
| Pi-hole DNS | 10.x.x.5 | — | Primary DNS for all LAN (runs on CT 107) |
| CT 100 — hermesagent | 10.x.x.100 | Node A | AI Orchestration Agent |
| CT 101 — zeek | 10.x.x.101 | Node B | Network IDS Sensor |
| CT 102 — pialert | 10.x.x.102 | Node A | Network Alerting |
| CT 103 — ripper | 10.x.x.103 | Node B | Media Automation |
| CT 104 — micromd | 10.x.x.104 | Node B | MDM Server |
| CT 105 — wazuh | 10.x.x.105 | Node A | SIEM Manager |
| CT 106 — grafana | 10.x.x.106 | Node A | Monitoring Hub |
| CT 107 — pihole | 10.x.x.107 | Node A | DNS Filter |
| CT 108 — portainer | 10.x.x.108 | Node A | Container Management |
| CT 109 — heimdall-dashboard | 10.x.x.109 | Node A | Service Dashboard |
| CT 110 — media-stack | 10.x.x.110 | Node B | Media Stack Host |
| CT 111 — immich | 10.x.x.111 | Node B | Photo Management |
| CT 112 — nextcloud | 10.x.x.112 | Node B | File Sync & Share |
| CT 113 — hermes-ollama | 10.x.x.113 | Node A | Local LLM Inference |
| CT 114 — cockpit | 10.x.x.114 | Node A | Centralized Management |
| VM 200 — dc-2025 | 10.x.x.200 | Node A | Domain Controller (Windows Server 2025) |
| VM 201 — win-client | 10.x.x.201 | Node A | Domain Client (Windows 11) |

---

## ⚠️ Critical Notes

1. **Webhook URLs** are NOT stored here — they're in the monitoring stack `.env` file
2. **SSH private keys** are NOT stored here — they live on the management CT
3. **Update this doc** immediately when passwords change
4. **All IPs shown** are sanitized 10.x.x.x placeholders — substitute with actual subnet addresses
5. **This repo is PUBLIC** — never commit real IPs, passwords, tokens, or keys