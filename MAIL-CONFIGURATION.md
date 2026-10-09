# Mail Configuration & SMTP Credentials 🔐

> **INTERNAL ONLY** — This doc tracks *where* mail credentials live for rotation.
> Values are placeholders only — the real app password lives in Vaultwarden.
> **Last updated:** Aug 13, 2026

All three identity/helpdesk services send mail through **Gmail SMTP**
(`smtp.gmail.com:587`, STARTTLS).

| | |
|---|---|
| **Sender address** | `${MAIL_USER}` = `piperlabsit@gmail.com` |
| **App password** | `${MAIL_APP_PASSWORD}` — store in Vaultwarden, NOT here |
| **SMTP host** | `smtp.gmail.com` |
| **Port / encryption** | `587` / STARTTLS |

> App passwords are 16-char tokens generated at
> `myaccount.google.com/apppasswords`. Rotating = generating a new one there,
> then updating the **three** locations below.

---

## Where the credentials live (rotation checklist)

### 1. Snipe-IT — CT 121 `10.0.20.121`
- **File:** `/opt/snipe-it/.env` (on CT121)
- **Vars:** `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
  `MAIL_FROM_ADDR`, `MAIL_FROM_NAME`
- **To apply a change:**
  ```bash
  cd /opt/snipe-it
  docker compose stop app && docker compose rm -f app && docker compose up -d app
  ```
  (env_file only loads on container *creation*, not restart)

### 2. osTicket — CT 122 `10.0.20.122`
- **File:** `/etc/msmtp` **inside** the `osticket-app` container
  (managed at `/opt/osticket/docker-compose.yml` via `SMTP_*` env vars)
- **Vars (compose):** `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USER`,
  `SMTP_PASSWORD`, `SMTP_TLS`
- **DB email table:** `ost_email` rows (admin "Support" = `piperlabsit@gmail.com`)
- **To apply a change:** update compose `SMTP_*` vars, then
  `docker compose up -d` and re-copy `/etc/msmtp` into the container
  (`docker cp`) or restart the container so its entrypoint re-populates it.

### 3. Keycloak — CT 120 `10.0.20.120`
- **Location:** realm `master` → `smtpServer` (set via admin REST API, not kcadm)
- **Keys:** `host`, `port`, `from`, `fromDisplayName`, `starttls`, `auth`,
  `user`, `password`
- **To apply a change:** admin API `PUT /admin/realms/master` with the
  `smtpServer` map. Note: kcadm CLI `-s 'smtpServer.x=...'` silently fails to
  nest — use the REST JSON body instead.
- New realms each need their own `smtpServer` config (copy these values).

---

## Rotation procedure
1. Generate a new app password at `myaccount.google.com/apppasswords`
2. Update the three locations above (Snipe-IT `.env`, osTicket compose+`/etc/msmtp`, Keycloak realm)
3. Send a test email from each to confirm (Snipe-IT: tinker `Mail::raw`; osTicket: `msmtp -C /etc/msmtp -t`; Keycloak: realm test-user `execute-actions-email`)
4. Revoke the old app password in Google
5. Update the Vaultwarden entry

---

## Related
- `homelab-service-migration` — the LXC split (CT120/121/122) that this mail config was applied to
