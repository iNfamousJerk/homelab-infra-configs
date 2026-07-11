# Grafana Monitoring Stack Beginner's Manual — <username>'s Homelab

*Tailored to your actual setup.*

---

## Section 1: What It Is

**Grafana is your homelab's mission-control dashboard.**

Imagine your homelab is a spacecraft. All the little sensors — CPU temps, disk usage, network traffic, whether services are up or down, how many containers are running — are scattered across different panels. Grafana pulls all those readings into one unified, beautiful glass cockpit so you can see the health of everything at a glance.

Your Grafana instance sits on **CT106** (the "monitoring container") and is fed data by **Prometheus** — the data-collection engine that actually goes out and scrapes metrics from your services every few seconds. Think of Prometheus as the sensor network itself, and Grafana as the pilot's display screen.

Behind the scenes, your stack has **11 containers** all working together:

| Container | Job |
|---|---|
| Grafana | Visualizes everything |
| Prometheus | Collects & stores metrics |
| Alertmanager | Fires Discord alerts when things break |
| Uptime Kuma | Pings external URLs for uptime |
| cAdvisor | Container-level metrics |
| Gitea | Git repos (not monitoring, but lives here) |
| Node exporters | Exposes Linux system metrics |

---

## Section 2: Getting In

**URLs:**
- `http://10.x.x.xxx:3000` (direct IP on the homelab network)
- `https://grafana.local` (via Nginx Proxy Manager, if configured)

**Login credentials:**
- **Username:** `admin`
- **Password:** `<admin-password>`

> ⚠️ **First-time login:** Change the password if prompted. Your homelab is internal, but habits matter.

---

## Section 3: The Dashboard / What You See

When you log in, you land on the **Home** screen. The left sidebar is your navigation hub:

1. **Search (magnifying glass icon)** — Type "Homelab Overview" or paste in the dashboard UID `eebe828f` to find your main dashboard.
2. **Dashboards** — Browse all saved dashboards.
3. **Explore** — Ad-hoc query builder (advanced).
4. **Alerting** — See Alertmanager firing and silences.
5. **Configuration (gear icon)** — Data sources, users, teams.

### The Homelab Overview Dashboard

Your main dashboard (UID: `eebe828f`) shows:
- **System resource panels** — CPU, RAM, disk for each node
- **Container health** — Which containers are running/stopped (from cAdvisor)
- **Uptime status** — External service checks (from Uptime Kuma via Prometheus)
- **Network throughput** — Bandwidth on key interfaces
- **Temperature sensors** — If your hardware exposes them

Each panel has a title, a time-series graph or gauge, and a small dropdown in the top-right corner to adjust the time range (last 6h, last 24h, last 7d, etc.).

---

## Section 4: How to Read / Use It

### Key Fields to Understand

**Time Range Selector** (top right) — Controls how far back you're looking. Default is "Last 6 hours". For troubleshooting, start with the last 1-2 hours so you see the current state clearly.

**Panel Legends** — Each colored line on a graph corresponds to a label (e.g., `instance="10.x.x.xxx:9100"`). Click a legend entry to isolate that line.

**Units of Measure:**
- `%` = percentage (CPU usage, disk usage)
- `bytes/sec` = network throughput
- `ms` = latency or response time
- `count` = event counts (HTTP requests, alerts)

**Dashboard Variables** (dropdowns at the top of the dashboard) — These let you filter. For example, a `node` variable lets you pick a specific server to view metrics for only that machine.

### Prometheus Data Sources

Grafana doesn't store data — it asks Prometheus. Your setup defines **40 Prometheus targets** across **9 jobs**:

- `node` — System metrics from every CT/VM
- `cadvisor` — Container metrics
- `uptime` — Uptime Kuma checks
- `gitea` — Gitea application metrics
- `alertmanager` — Alertmanager itself
- `prometheus` — Prometheus self-metrics

> 💡 If a panel shows "No data", a target is probably down. Check Prometheus targets at the datasource settings or look at the Targets page in Prometheus UI (port 9090 on the same IP).

---

## Section 5: Beginner Routine

**Daily (1 minute):**
1. Open Grafana → Homelab Overview dashboard
2. Scan the panels for any red/orange values
3. Check the "Last 24 hours" view for overnight issues

**Weekly (5 minutes):**
1. Look at disk-usage trends — are any volumes filling up?
2. Review Alertmanager for any repeated firing alerts you've been ignoring
3. Check that all 40 Prometheus targets are reporting (if you see fewer, something stopped scraping)

**Monthly (10 minutes):**
1. Browse the Explore tab and try a PromQL query like `node_load1` to see if you understand the query language better
2. Update any dashboard panels to add new services you've deployed
3. Review alert rules — silence stale ones, add missing ones

---

## Section 6: Quick Reference Card

| Item | Value |
|---|---|
| **Grafana URL** | http://10.x.x.xxx:3000 |
| **Alternate URL** | https://grafana.local |
| **Login** | admin / <admin-password> |
| **Host CT** | CT106 (monitoring container) |
| **Containers in stack** | 11 (Grafana, Prometheus, Alertmanager, Uptime Kuma, cAdvisor, Gitea, exporters) |
| **Prometheus targets** | ~40 across 9 jobs |
| **Homelab dashboard UID** | eebe828f |
| **Prometheus UI** | http://10.x.x.xxx:9090 |
| **Alertmanager UI** | http://10.x.x.xxx:9093 |

**Common fixes:**
- *"No data" panel* → Check if the related Prometheus target is up on port 9090
- *Dashboard won't load* → Re-enter the UID `eebe828f` in the dashboard search
- *Can't log in* → Reset via Grafana CLI: `docker exec grafana grafana-cli admin reset-admin-password NewPass`

---

*Generated for <username>'s homelab.*
