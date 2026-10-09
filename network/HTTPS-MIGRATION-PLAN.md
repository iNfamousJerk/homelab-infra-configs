# HTTPS Migration Plan — all NPM-proxied services on TLS

**Status:** PLAN — not yet executed. To be configured by the operator.

## Goal
Serve every NPM-reverse-proxied service over **https** with a **trusted**
certificate (no browser warning), replacing the current http-only and
per-host self-signed setups.

## Current state (verified 2026-09-25)

| Scheme | Hosts |
|--------|-------|
| **https (have cert)** | `nextcloud.piper.lan`, `keycloak.piper.lan`, `vaultwarden.piper.lan` |
| **http only (need cert)** | `radarr`, `sonarr`, `lidarr`, `bazarr`, `prowlarr`, `jellyfin`, `seerr`, `immich`, `komga`, `librarr`, `navidrome`, `audiobookshelf`, `grafana.lan`, `prometheus.lan`, `kuma`, `gitea.lan`, `qbittorrent`, `pihole.lan`, `patchmon`, `snipeit`, `osticket` — all `.piper.lan` unless noted, all current http |
| **management (skip / optional)** | `pve.lan`, `pve2.lan` (no `pve3`), `opn.piper.lan`, `flaresolverr.piper.lan` |

That is **21 services** to convert.

---

## Strategy — internal CA (recommended)

Per-host self-signed certs (the current Keycloak/Nextcloud pattern) make each
browser show a warning for *every* host until accepted once — 21 warnings is
worse than one. An **internal CA** means:

1. Create **one** private CA cert + key.
2. Issue a **leaf cert per service** signed by that CA.
3. **Install the CA into each device/browser** once → every service then loads
   with **zero warnings**.

> **Caveat:** native clients that use their own trust store or pin certs
> (e.g. **Roku/Moonfin for Jellyfin**, some mobile apps) may still refuse a
> private CA. Those paths keep using tailnet `https://…taile1ed4c.ts.net` (which
> gets a real Let's Encrypt cert via Tailscale Serve) or fall back to http.
> The browser-based dashboard is fully trusted after the one-time CA install.

---

## Part 1 — Create the CA and issue certs

Run on one host (e.g. the Hermes CT or CT144 NPM host). Keep the **CA key
offline-ish** — it signs everything.

```bash
# 1. CA (long-lived, e.g. 10 years)
mkdir -p /opt/npm/data/custom_ssl/migration-ca && cd /opt/npm/data/custom_ssl/migration-ca
openssl req -x509 -newkey rsa:4096 -nodes -days 3650 -keyout ca.key \
  -out ca.pem -subj "/CN=Homelab Internal CA" \
  -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=keyCertSign,cRLSign"

# 2. Per-host leaf (repeat for each service hostname)
#    SAN(s): the piper.lan hostname AND, where present, the bare .lan alias.
for H in radarr sonarr lidarr bazarr prowlarr jellyfin seerr immich komga \
         librarr navidrome audiobookshelf qbittorrent pihole patchmon snipeit \
         osticket; do
openssl req -new -newkey rsa:2048 -nodes -keyout $H.key -out $H.csr \
  -subj "/CN=$H.piper.lan"
openssl x509 -req -in $H.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
  -out $H.pem -days 825 -sha256 \
  -extfile <(printf "subjectAltName=DNS:$H.piper.lan\nbasicConstraints=CA:FALSE")
done
# same for the .lan-only hosts: grafana.lan prometheus.lan gitea.lan kuma → use CN=grafana.lan etc.
```

> **Gitea note:** Gitea's `GITEA__server__ROOT_URL` is currently
> `http://10.0.7.125:3002` (corrected in this repo's `docker-compose.yml`).
> When you proxy it over https it must become **`https://gitea.lan`** or Gitea
> will generate http redirects/links. Edit its env + restart the container.

## Part 2 — Install the CA on clients (one-time)

- **Linux/browsers (Firefox/Chrome on Debian-Mint):** copy `ca.pem` to
  `/usr/local/share/ca-certificates/` then `sudo update-ca-certificates`.
  Firefox additionally: Settings → Privacy & Security → Certificates → import.
- **Windows:** `certutil -addstore "Root" ca.pem` (as admin).
- **macOS:** open the cert in Keychain Access → Always Trust.
- **iOS/Android:** install `ca.pem` profile and enable full trust (iOS Settings →
  General → About → Certificate Trust Settings; Android must be a
  user-installed CA and apps that use the system store honor it).

## Part 3 — Wire each cert into NPM

Two ways; pick one:

- **NPM UI** (if you get access): each proxy host → SSL tab → "Custom SSL"
  → select the leaf cert + key.
- **Hand-edit + reload** (current pattern; NPM UI password unknown):
  for each `proxy_host/<id>.conf` add the 443 listener + cert lines:

```nginx
  listen 443 ssl;
  listen [::]:443 ssl;
  ssl_certificate     /data/custom_ssl/migration-ca/<host>.pem;
  ssl_certificate_key /data/custom_ssl/migration-ca/<host>.key;
```
Then `docker exec npm nginx -t && docker exec npm nginx -s reload` (or use the
`npm` container name as configured).

Optionally add an `http → https` redirect block (301) per host so `http://host`
bounces to `https://host`.

> **Keep port 80 listening** while switching, and only add the redirect after
> https is verified on a host (avoid locking yourself out mid-change).

## Part 4 — Per-service config so https is correct

Most work as-is IF the NPM proxy forwards the right headers
(`host`, `x-forwarded-proto`, `x-forwarded-for`, `proto`) — NPM does this by
default. Services that need explicit config:

| Service | What to set |
|---------|-------------|
| **nextcloud** | done — `overwriteprotocol => https` already |
| **gitea** | `ROOT_URL=https://gitea.lan` (see Part 1 note); restart |
| **immich** | verify OIDC/(external URL) uses https; set `IMMICH__SERVER__EXTERNAL_DOMAIN=https://immich.piper.lan` if the app shows http links |
| **grafana** | leave `root_url` as subdomain `https://grafana.lan` (not subpath) |
| **arrs / prowlarr / bazarr** | ensure the proxy passes `X-Forwarded-Proto` (NPM default) so they emit https; no BaseUrl needed for a dedicated subdomain |
| **jellyfin / seerr / navidrome / ABS / others** | usually none; verify via the https URL, check for mixed-content warnings in browser devtools |

## Part 5 — Verification (per host)

- `curl -skI https://<host>` → expect `200`/`302` (not `502`/`000`)
- `echo | openssl s_client -connect <host>:443 -servername <host>` →
  `subject=CN=<host>…`, `Verify return code: 19/20` *before* CA install (expected
  — the CA isn't trusted yet), **0 (ok)** *after* installing the CA on that box
- SAN must contain the hostname (`DNS:<host>`); if the cert lacks the host you'll
  get a `NET::ERR_CERT_COMMON_NAME_INVALID`
- Dashboard tiles: each should already point at the NPM hostname (done); after
  https is live, flip the tiles from `http://` to `https://` where you want it.

## Rollback
- NPM: remove the 443 block → returns to http-only proxy (no lingering change).
- Service: revert any `ROOT_URL`/`overwriteprotocol` edit.
- CA: uninstalling it makes clients reject private-CA certs (that's expected);
  keep a copy of `ca.pem` + `ca.key` backed up so you can re-issue/re-trust.

---

## Recommended order
1. Create CA + issue the 21 leaf certs (+ `gitea` ROOT_URL edit).
2. Install CA on **one** browser → prove one service works end-to-end.
3. Roll out the NPM http→https per service, verify each, then move on.
4. After all verified, install the CA on remaining devices, then flip the
   `http://` Homarr tiles to `https://`.
5. Optional: add http→https 301 redirects per host once stable.
