# Client Portal + GPU-Transcoded Streaming — Sanitized Reference

> Sanitized reference for a self-hosted multi-tenant **client portal** with GPU-accelerated
> media streaming. No real addresses, hostnames, or identifying details. Hardware and
> service names are abstracted per the public-repo convention.

## The Model: One Container Per Client (Tenant Isolation)

For **clients**, the container is the **tenant boundary** — all of one client's services
run in a single container with one container orchestration stack. This deliberately
differs from the operator's own homelab convention (one service per container).

**Why tenant-per-container:**
- **Isolation / blast-radius:** each client's stack is fully walled off; a compromise or
  misconfiguration in one client's stack can't reach another client or the operator's own
  infrastructure.
- **Clean teardown / billing:** client leaves → stop + delete the container = everything
  gone, nothing lingers in a shared host.
- **Per-client resources:** pin RAM/CPU per container; no contention with operator services.
- **Backup scoping:** one container = one backup unit; you know exactly what each client has.
- **Reusable template:** clone a client container config → swap the per-client env
  (client ID, media paths, credentials) → new tenant.

### Shared vs. per-client

| Layer | Shared (single instance) | Per-client (one per container) |
|-------|--------------------------|-------------------------------|
| Identity provider (SSO) | ✅ single instance | — |
| Reverse proxy | ✅ single instance | — |
| VPN coordination plane | ✅ single instance | ✅ one node per client container |
| Container orchestration stack | — | ✅ one stack per client container |
| Streaming / photo / file / portal | — | ✅ per client stack |

---

## Why All-VPN (the decision)

| Path | Public ports | Public domain | Mobile-app HTTPS | Attack surface |
|------|--------------|---------------|------------------|----------------|
| Public portal + reverse proxy + ACME | 80,443 WAN | Yes | Let's Encrypt | Login pages brute-forceable 24/7, reverse proxy exposed, WAN IP visible |
| **All-VPN (chosen)** | **None** | **No** | Auto-trusted VPN certs | Only the VPN coordination plane; revoke = remove node |

The chosen mesh VPN issues **automatically-trusted TLS certificates** for its `*.vpn.net`
style hostnames — exactly what mobile apps (photo backup, file sync, streaming) demand
(self-signed certs are rejected by mobile apps). No cert warnings, no ACME renewal, no
DNS configuration.

**The one requirement:** every client installs the VPN app on their device and the operator
shares the specific client node(s) with them. That is the entire cost of "no public domain
+ zero exposure."

---

## Target Architecture

```
CLIENT A CONTAINER (CT 2xx) ── one orchestration stack ── Docker
  ├── streaming   (GPU NVENC via passthrough)
  ├── photo       (photo backup)
  ├── file        (file sync)  [optional per client]
  └── portal      (tile dashboard)
       │
       ├── VPN node → https://portal-<client>.<vpn>.ts.net
       ├── VPN node → https://photo-<client>.<vpn>.ts.net  (mobile apps)
       └── reverse proxy terminates HTTPS → SSO → tiles

CLIENT B CONTAINER (CT 2xx) ── identical shape, own CT / VPN node / realm users
```

---

## Phase 1 — Provision a Client Container (template)

For each client, create a container on the appropriate hypervisor node with nesting
enabled (container orchestration needs it), enough RAM/CPU for that client's stack, and a
media bind-mount:

```bash
pct create 2XX <template-vmid> \
  --hostname client-N --storage local-lvm \
  --memory 4096 --cores 2 --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --features nesting=1 \
  --mp0 /mnt/media,mp=/data/media
```

Deploy the container runtime inside the LXC once; **clone this LXC as the base for each
new client**:

```bash
# Base client LXC = CT 200 (stopped). Clone for Client A:
pct clone 200 201 --hostname client-a
pct start 201
```

---

## Phase 2 — Per-client Orchestration Stack

Inside each client container, a single `/opt/<client>` stack holds all that client's
services. Skeleton:

```yaml
# /opt/client-a/docker-compose.yml
services:
  streaming:
    image: <streaming-server-image>
    devices:                      # GPU NVENC passthrough
      - /dev/nvidia0:/dev/nvidia0
      - /dev/nvidiactl:/dev/nvidiactl
      - /dev/nvidia-modeset:/dev/nvidia-modeset
      - /dev/nvidia-uvm:/dev/nvidia-uvm
    volumes:
      - ./streaming/config:/config
      - /data/media:/media:ro
    ports:
      - "8096:8096"

  photo:
    image: <photo-server-image>
    volumes:
      - ./photo/library:/usr/src/app/upload
      - ./photo/postgres:/var/lib/postgresql/data
    environment:
      - ML_ENABLED=true
    ports:
      - "2283:3001"

  portal:            # optional per client
    image: <dashboard-image>
    ports:
      - "7575:7575"
    volumes:
      - ./portal/configs:/app/data/configs
      - ./portal/icons:/app/public/icons
```

Git-track the stack (operator convention): push `stack-client-a` to private git. Each
client's config lives in the same container, so teardown = delete the container.

---

## Phase 3 — GPU Passthrough into the Client Container

> A discrete NVIDIA GPU uses `/dev/nvidia*` nodes + NVENC, **NOT** an integrated-GPU
> `/dev/dri`/QuickSync recipe — don't mix them.

### 3a. NVIDIA driver on the hypervisor host
```bash
apt install -y nvidia-driver <kernel-headers>
lsmod | grep -E 'nvidia|nvidia_uvm'
ls -l /dev/nvidia0 /dev/nvidiactl /dev/nvidia-modeset /dev/nvidia-uvm
```

### 3b. Pass GPU into the client container
Append to `/etc/pve/lxc/2XX.conf`:
```
lxc.mount.entry: /dev/nvidia0 dev/nvidia0 none bind,optional,create=file
lxc.mount.entry: /dev/nvidiactl dev/nvidiactl none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-modeset dev/nvidia-modeset none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm dev/nvidia-uvm none bind,optional,create=file
lxc.cgroup2.devices.allow: c 195:0 rwm
lxc.cgroup2.devices.allow: c 195:255 rwm
```
Then reboot the container.

### 3c. Driver inside the container
Install matching NVIDIA driver + NVENC libs inside the container so the streaming
server's ffmpeg uses NVENC. Verify with `nvidia-smi`.

### 3d. Streaming config
Playback settings → Hardware acceleration: **NVENC (NVIDIA)**. Confirm transcodes hit the
GPU via `nvidia-smi` during a play.

> **Shared-GPU note:** a single physical GPU is shared across client containers that need
> transcoding. The driver handles concurrent sessions, but throughput is shared. For hard
> per-client isolation, a second GPU is required. Fine for a small number of clients.

---

## Phase 4 — VPN per Client

Each client container gets its **own VPN node**:
```bash
pct exec 2XX -- bash -s <<'EOF'
curl -fsSL <vpn-installer> | sh
<vpn> up
EOF
```
Enable **MagicDNS + HTTPS certs** in the VPN admin console. Mint certs for the client's
hostnames on the reverse-proxy host.

**Share with the client:** in the VPN admin console, share ONLY that client's node(s) with
their email — never the whole network. Revoke later by removing their access.

---

## Phase 5 — Reverse Proxy + `*.vpn` HTTPS

The reverse proxy (NPM-style) proxies to the client's VPN-resolved names with the VPN's
auto-trusted certs:

1. `tailscale cert portal-<client>.<tailnet>.ts.net` on the reverse-proxy host → upload
   cert+key (custom/"other" provider).
2. Proxy hosts per client service, `forward_host` = the client container's **VPN IP**
   (`<vpn> ip -4` on the container), keeping the proxy path inside the encrypted VPN.

| Domain (VPN DNS) | Forward to |
|------------------|-----------|
| `portal-<client>.<vpn>.ts.net` | client container :7575 |
| `photo-<client>.<vpn>.ts.net` | client container :2283 |
| `file-<client>.<vpn>.ts.net` | client container :443/:80 (optional) |
| `streaming-<client>.<vpn>.ts.net` | client container :8096 |

**Cert auto-renew:** VPN certs expire every ~90 days — schedule renewal (cron).

---

## Phase 6 — SSO (per-client realm)

Recommend **one realm per client** to match the container boundary (or one shared realm
with per-client users if simpler).

1. Create the client realm (e.g. `client-a`). **No admin console access** for the client,
   email verified, no 2FA.
2. OIDC clients in that realm with correct redirect URIs:
   - `portal` → `https://portal-<client>.<vpn>.ts.net/*`
   - `photo` → `https://photo-<client>.<vpn>.ts.net/auth/login`
   - `file` → the file-sync app's OIDC redirect
3. Create the client user(s); real password, temporary OFF.
4. **Change the default admin credentials** before anything client-facing.
5. **Export the realm** before adding clients — exports are the only non-destructive
   recovery for the embedded database.

> **Go-live blocker:** run the SSO provider in **production mode** (external database +
   `start` mode + HTTPS), not development mode, before handing an external client access.

---

## Phase 7 — Photo / File SSO (native OIDC)

- **Photo:** Settings → Authentication → OIDC; realm issuer, client ID, redirect
  `https://photo-<client>.<vpn>.ts.net/auth/login`.
- **File:** enable OIDC login app; provider = client realm issuer, client ID.
- Mobile apps point at the `*.vpn` host over the VPN — auto-trusted certs.

---

## Phase 8 — Portal Tiles

Per-client dashboard tiles open each service's `*.vpn` URL. Optionally brand per client.
Wire the portal's OIDC "Issuer URL" to the **client realm base URL** — NOT the discovery
document URL (a wrong issuer is rejected as invalid).

---

## Go-Live Checklist (safety / DR)

- [ ] SSO default admin changed.
- [ ] SSO realm(s) **exported** before adding clients.
- [ ] VPN: share ONLY the client's node(s), not the whole network.
- [ ] Media pool backed up (backup server). Confirm each client container's config dir is
      in backup scope.
- [ ] Test from a **client-side device on cellular** (off the operator's LAN):
  - Portal loads with the `*.vpn` cert (no warning).
  - SSO login → tiles → each app opens.
  - Photo/file mobile apps connect and sync.
  - Streaming plays and transcodes via the GPU.

---

## Open Items to Resolve

1. **SSO production mode** before go-live (external database + `start` mode + HTTPS).
2. **Container ID range for clients** (suggest CT 2xx, keeping 1xx for operator infra).
3. **Realm strategy** — one realm per client (recommended) vs. one shared realm.
4. **Which services per client** — default streaming + photo; file/portal optional.
5. **GPU hardware check** — power connector + case clearance; and whether concurrent
   client transcoding needs a second GPU.
6. **Client onboarding UX** — one-pager (install VPN → accept share → open portal URL).

---

## Client Onboarding One-Pager (template)

> Edit the bracketed placeholders per client before sending.

### Welcome to [CLIENT NAME]'s Portal

Your services are ready. Everything runs over a private, encrypted connection — you never
connect over the public internet.

1. **Install the VPN app** on your phone (app store) and laptop/desktop
   (<https://example-vpn.com/download>). Sign in with the email you'll receive the invite on.
2. **Accept the share invite** you receive by email (or link). It grants access only to
   your own portal, nothing else.
3. **Open your portal:**
   - **Dashboard (web):** `https://portal-<CLIENT_NAME>.<vpn>.ts.net` — log in with the
     credentials we set up. Click a tile to open streaming, photos, or files.
   - **Photos (phone app):** install the photo app, add a server, point it at
     `https://photo-<CLIENT_NAME>.<vpn>.ts.net` while connected to the VPN.
   - **Files (optional):** install the file-sync app, point it at
     `https://file-<CLIENT_NAME>.<vpn>.ts.net`.
   - **Streaming:** open `https://streaming-<CLIENT_NAME>.<vpn>.ts.net` or the streaming
     app. Hardware transcoding keeps playback smooth on slower connections.

**Notes:** Keep the VPN on while using the portal. You may see a second login at the
streaming app — that's expected (it manages its own accounts). Forgot a password? Contact
us to reset it. We can revoke your access at any time. Heavy 4K streams may need a faster
upload on our side; tell us if playback stutters.

---

### Internal support notes (not for the client)

- Client access is **VPN-only**; the client's container is a single CT with one stack.
  Teardown = stop + delete CT + remove VPN node share + delete realm.
- Revocation: remove the client's node access in the VPN admin console, and disable their
  SSO realm user. Both take effect immediately.
- Support triage: check the stack status + logs in the client container, then the `*.vpn`
  hostname resolves, then the reverse-proxy host, then the SSO realm.
