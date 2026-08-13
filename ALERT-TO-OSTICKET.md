# Alert-to-osTicket Pipeline 🔔

Automatically opens an osTicket helpdesk ticket when a **critical** Prometheus
alert fires, using Hermes as the AI middleware.

> **INTERNAL ONLY.** Sanitized — no credentials/API keys in this file.
> **Last updated:** Aug 13, 2026

## Architecture

```
[CT106] Alertmanager :9093 ──(Hermes polls every 2 min)──▶
[CT100] Hermes cron job → parse critical alert → enrich → osTicket API
                                                              ▼
[CT122] osTicket :8081 ◀── ticket opened (subject, severity, instance, details)
```

**Why poll, not webhook:** CT100 (Hermes) is an **unprivileged LXC**, which
silently drops inbound connections on ports >1024. Alertmanager cannot push a
webhook to Hermes. Outbound polling works fine, so Hermes pulls instead.

**AI role:** the Hermes poller reads each alert, extracts alertname / severity /
instance / summary / detail / generator URL, formats a human-readable ticket,
and files it via the osTicket API.

## Scope / Noise control

- **Critical severity only** (info/warning stay in Discord, not osTicket).
- **Deduplicated:** each alert `fingerprint` is ticketed once. When the alert
  resolves, its fingerprint is forgotten, so a re-fire creates a new ticket.
- Configurable via `WATCHED_SEVERITIES` in the poller script.

## Components

| Piece | Location |
|-------|----------|
| Poller script | CT100 `/home/hermes/.hermes/scripts/alert-to-osticket.py` |
| Cron wrapper | CT100 `/home/hermes/.hermes/scripts/alert-osticket-cron.sh` |
| Hermes cron job | `Alert-to-osTicket poller` (every 2 min, `no_agent`) |
| State (dedup) | CT100 `/home/hermes/.hermes/alert_ticket_state.json` |
| osTicket API key | CT122 `/root/osticket_api_key.txt` + CT100 `~/.hermes/alert_osticket_key.txt` |
| osTicket API key row | `ost_api_key` table (key `C646…`, IP-restricted to CT100) |

## osTicket API setup (prereq)

1. osTicket API is enabled by an **active API key row** in `ost_api_key`.
2. Create the key (IP-restricted to a single source — see pitfall below):
   ```sql
   INSERT INTO ost_api_key (isactive, ipaddr, apikey, can_create_tickets,
       can_exec_cron, notes, created, updated)
   VALUES (1, '10.2.7.107', '<KEY>', 1, 1, 'Hermes alert pipeline', NOW(), NOW());
   ```
3. Save `<KEY>` to `/root/osticket_api_key.txt` (chmod 600) on CT122, and copy
   to CT100 `~/.hermes/alert_osticket_key.txt` (chmod 600).
4. Endpoint: `POST http://<osTicket>/api/tickets.json` with header `X-API-Key`.
   Success = `HTTP 201` with the ticket number in the body.

## Rotation

- Regenerate key → update `ost_api_key` row + both key files.
- Store the key in Vaultwarden (Anthony manages it).

## Troubleshooting

- **401 "Valid API key required"** — `ipaddr` must be a **single exact IP**
  matching the caller. osTicket compares `ipaddr == REMOTE_ADDR` (string
  equality); a comma-separated list never matches. Call from CT100 (10.2.7.107).
- **400 "Incomplete client information"** — osTicket can't create a *new*
  client from a bare email. Use an email that's already a registered osTicket
  client (e.g. `piperlabsit@gmail.com`), or send the full user name object.
- **Dedup not firing** — check `alert_ticket_state.json` still has the
  fingerprint; it's only dropped after the alert leaves the active set.

## Related
- `homelab-alerting` skill — the Prometheus/Alertmanager/Discord pipeline this
  extends; Discord still receives all severities, osTicket only critical.
- `osticket-deployment` skill — osTicket service itself.
