# PVE1 → PVE2 Service Migration Guide

> **Purpose:** Step-by-step instructions for migrating LXC-based services from an existing Proxmox VE node (PVE1) to a new node (PVE2) with ZFS storage.

## Background: Why Fresh CTs Instead of Migrating the Container?

When I initially asked "should we migrate the container directly or create a fresh one?" you asked for my recommendation. Here's the reasoning behind **creating fresh CTs on PVE2** vs migrating the existing containers:

### Approach A: Container Migration (`pct migrate`)
Proxmox can live-migrate a container between nodes in a cluster. This would:
- Preserve the exact OS state, installed packages, config files, and data
- Keep the same container ID and network config
- Take ~minutes for the LVM volume transfer

**Downsides:**
- Still on LVM-thin storage (no checksums, no compression, no portability)
- Carries over years of cruft, unused packages, and temp files
- Misses the opportunity to clean-install updated versions of dependencies (PHP, Node, PostgreSQL, etc.)
- LVM-thin volumes can't be easily moved to a different system if the host dies — they're tied to the PVE1 volume group

### Approach B: Fresh CT + Data Sync (What We Did)
Create a new container on PVE2 with ZFS root + data datasets, then rsync data:

**Benefits:**
- **ZFS checksumming** detects and repairs silent data corruption
- **ZFS portability** — the pool can be imported on any Linux system. If PVE2's motherboard dies, pull the drives, plug into any machine with ZFS, and `zpool import media` to get all data back
- **ZFS compression** (lz4/zstd) saves disk space with near-zero performance cost
- **ZFS snapshots** for point-in-time recovery before risky operations
- **Clean state** — fresh Debian install means no cruft, smaller backups, fewer attack surfaces
- **Updated dependencies** — newer PostgreSQL, PHP, Apache, Node.js versions than the original 1-2 year old installs
- **PBS backup compatibility** — PBS uses Proxmox backup client with snapshot integration, much faster than file-level backups

### When to Use Migration Instead
Container migration makes sense when:
- The service has complex, hard-to-replicate configuration (AD domain controllers, custom databases with tricky replication)
- Uptime matters more than clean state (migration takes minutes, rebuild takes hours)
- The container has extensive firewall rules, network namespaces, or systemd-nspawn setups that are painful to reproduce

For media stacks, file sync, and photo management — services where **data portability and integrity matter more than uptime** — fresh CT + rsync is the right call.

---

## General Migration Pattern

This pattern was followed for each service. Adapt as needed for future migrations.

```
Phase 1: Prepare               Phase 2: Provision            Phase 3: Sync & Configure
┌─────────────────┐           ┌─────────────────────┐        ┌─────────────────────────┐
│ 1. Inventory     │           │ 4. Create CT on PVE2│        │ 7. Rsync app files      │
│    - App files   │ ────────▶ │    - Debian 12/13   │ ─────▶│ 8. Rsync user data      │
│    - Data dirs   │           │    - 2C/4GB (adjust)│        │ 9. Rsync database dump  │
│    - Database    │           │    - Assign temp IP │        │10. Install dependencies │
│    - Config      │           │    - Create ZFS ds  │        │11. Restore DB           │
│ 2. Measure size  │           │    - Bind mount ZFS │        │12. Fix permissions      │
│ 3. Take ZFS snap │           │    - Install base OS│        │13. Configure services   │
│    on old data   │           │ 5. Create ZFS ds on │        │14. Test on temp IP      │
└─────────────────┘           │    pool             │        └──────────┬──────────────┘
                              │ 6. SSH key setup    │                   │
                              └─────────────────────┘                   ▼
                                                              Phase 4: Cutover
                                                           ┌─────────────────────────┐
                                                           │15. Stop old services    │
                                                           │16. Final rsync (deltas) │
                                                           │17. Swap to prod IP      │
                                                           │18. Start new services   │
                                                           │19. Verify HTTP 200      │
                                                           │20. Destroy old CT       │
                                                           └─────────────────────────┘
```

---

## Phase 1: Inventory & Prepare (on PVE1)

### 1.1 Inventory the Existing Service

```bash
# SSH into PVE1
ssh root@10.2.7.x

# Find the container
pct list | grep <service-name>

# Enter it
pct enter <CTID>

# Document:
# - What OS/version
cat /etc/os-release

# - What packages are installed (grab the essentials list)
dpkg -l | grep -E 'nginx|apache|php|mysql|mariadb|postgresql|redis|node' | awk '{print $2, $3}'

# - Where app files live (typically /var/www/<app> or /opt/<app>)
find /var/www /opt -maxdepth 2 -type d 2>/dev/null

# - Where user data lives
find / -maxdepth 3 -name 'data' -type d 2>/dev/null

# - What services exist
systemctl list-units --type=service --state=running | grep -E '<app>|nginx|apache|php|mysql|postgres|redis'
```

### 1.2 Measure Data Sizes

```bash
# App files
du -sh /opt/<app> /var/www/<app> 2>/dev/null

# User data
du -sh /path/to/user/data

# Database
# MySQL/MariaDB:
mysql -u root -e "SELECT table_schema AS 'Database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' FROM information_schema.tables GROUP BY table_schema;"

# PostgreSQL:
sudo -u postgres psql -c "SELECT pg_database_size('dbname')/1024/1024||' MB' AS size;"

# Total data to transfer
du -sh /var/www/<app> /path/to/user/data
```

### 1.3 Take ZFS Snapshot (if old data is on ZFS or LVM)

```bash
# LVM snapshot (read-only, crash-consistent)
lvcreate -L5G -s -n <service>-pre-migrate /dev/pve/vm-<CTID>-disk-0 && echo "LVM snap created"

# You'll use this as the source for rsync to get a consistent filesystem view
```

### 1.4 Dump the Database

```bash
# MySQL/MariaDB
mysqldump -u root --all-databases --single-transaction --quick > /tmp/<service>-db.sql

# PostgreSQL
sudo -u postgres pg_dump -d <dbname> --format=custom -f /tmp/<service>.dump
# Or plain SQL:
sudo -u postgres pg_dump -d <dbname> > /tmp/<service>.sql

# Compress
gzip /tmp/<service>-db.sql
```

---

## Phase 2: Provision New CT on PVE2

### 2.1 Create the Container

```bash
# SSH into PVE2
ssh root@10.2.7.x

# Create CT (adjust CTID, storage, cores, memory for each service)
pct create <CTID> local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --storage local-lvm \
  --rootfs local-lvm:8 \
  --cores 2 \
  --memory 4096 \
  --net0 name=eth0,bridge=vmbr0,gw=10.2.7.x,ip=10.2.7.<temp_ip>/24 \
  --hostname <service-name> \
  --unprivileged 1 \
  --features nesting=1
```

### 2.2 Create ZFS Dataset for User Data

```bash
# Create a dataset on the ZFS pool
zfs create media/<service>_data

# Set mount point
zfs set mountpoint=/media/<service>_data media/<service>_data

# Enable compression
zfs set compression=lz4 media/<service>_data
```

### 2.3 Bind-Mount ZFS Dataset into the CT

```bash
# Bind mount the ZFS dataset into the CT
pct set <CTID> -mp0 /media/<service>_data,mp=/<data_mount_point>

# Verify it's mounted
pct enter <CTID> -- mount | grep <service>
```

### 2.4 Start CT and Install Base OS

```bash
pct start <CTID>
pct enter <CTID>

# Update
apt update && apt upgrade -y

# Install base tools
apt install -y curl wget sudo ufw

# Install service-specific dependencies (example patterns):

# For PHP-based services (Nextcloud, etc.):
apt install -y apache2 mariadb-server mariadb-client redis-server \
  php8.2 php8.2-{cli,fpm,curl,gd,intl,bcmath,json,mbstring,xml,zip,imagick,mysql,redis} \
  libapache2-mod-php8.2

# For Node.js-based services (Immich, etc.):
apt install -y postgresql-17 postgresql-client redis-server nginx python3 python3-venv
# Then install Node.js 24 via nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
source ~/.bashrc
nvm install 24
nvm use 24

# For Docker-based services:
apt install -y docker.io docker-compose-v2
```

### 2.5 Transfer SSH Keys (for rsync between old and new)

```bash
# From PVE2 host, copy SSH key to old PVE1 container
ssh-copy-id root@<old_CT_IP>

# Also ensure PVE2 can SSH to itself if rsyncing via host
ssh-copy-id root@10.2.7.x
```

---

## Phase 3: Sync Data & Configure

### 3.1 Rsync App Files

```bash
# From PVE2 host or CT
# First rsync — exclude user data, node_modules, cache
rsync -av --info=progress2 \
  --exclude 'node_modules' \
  --exclude 'cache' \
  --exclude 'uploads' \
  --exclude 'data' \
  root@<old_CT_IP>:/opt/<app>/ /opt/<app>/
```

### 3.2 Rsync User Data to ZFS

```bash
# Directly to ZFS mount for portable storage
rsync -av --info=progress2 \
  root@<old_CT_IP>:/path/to/user/data/ /media/<service>_data/
```

### 3.3 Transfer Database Dump

```bash
# Copy the dump file from old CT
scp root@<old_CT_IP>:/tmp/<service>-db.sql.gz /tmp/

# Decompress
gunzip /tmp/<service>-db.sql.gz
```

### 3.4 Restore Database

```bash
# MySQL/MariaDB:
mysql -u root < /tmp/<service>-db.sql

# PostgreSQL:
sudo -u postgres pg_restore --dbname=<dbname> --format=custom /tmp/<service>.dump
# Or for SQL dumps:
sudo -u postgres psql -d <dbname> < /tmp/<service>.sql
```

### 3.5 Fix Permissions for Unprivileged CTs

**Critical:** Unprivileged Proxmox containers use UID mapping. A container's UID `N` maps to host UID `100000 + N`. Files on a host bind-mount into a container must be owned by the mapped host UID to be visible inside the CT.

```bash
# Determine the correct mapped UID:
# CT user        → Host UID
# www-data (33)  → 100033
# immich (999)   → 100999
# (100000 is the standard Proxmox UID offset)

# Apply on PVE2 HOST (not inside the CT):
chown -R <HOST_MAPPED_UID>:<HOST_MAPPED_GID> /media/<service>_data/
```

**Permission mapping reference:**

| CT User | CT UID | Host Mapped UID | Common Service |
|---------|--------|-----------------|----------------|
| root | 0 | 100000 | System |
| www-data | 33 | 100033 | Nextcloud, PHP |
| nobody | 65534 | 165534 | Default unmapped |
| immich* | 999 | 100999 | Immich |

*\* Immich runs as UID 999 inside the CT (set in systemd service file via `User=999`)*

### 3.6 Configure the Service

```bash
# Copy config files over or recreate them from scratch
# Point config at the ZFS mount for user data:
#   Nextcloud:   'datadirectory' => '/var/www/nextcloud-data'
#   Immich:      IMMICH_MEDIA_LOCATION=/opt/immich/upload

# Create systemd service files if needed (Immich)
# Configure web server (Apache vhost, Nginx site)
# Set up PHP-FPM pool if using Nextcloud
```

### 3.7 Test on Temporary IP

```bash
# Start the service
systemctl start <service>
systemctl enable <service>

# Verify HTTP response
curl -s -o /dev/null -w '%{http_code}' http://localhost:<port>/

# Check service logs
journalctl -u <service> -n 20 --no-pager
```

---

## Phase 4: Cutover

### 4.1 Stop Old Service on PVE1

```bash
ssh root@10.2.7.x
pct stop <old_CTID>
```

### 4.2 Final Delta Rsync (if any data changed during migration)

```bash
# Catch any changes since the first sync
rsync -av --delete root@<old_CT_IP>:/path/to/user/data/ /media/<service>_data/
```

### 4.3 Swap to Production IP

```bash
# On PVE2 — update the CT's IP to the production address
pct set <CTID> --net0 name=eth0,bridge=vmbr0,gw=10.2.7.x,ip=10.2.7.<prod_ip>/24

# Restart the CT
pct stop <CTID> && pct start <CTID>
```

### 4.4 Verify Production Access

```bash
# From PVE2 host or any machine on the LAN
curl -s -o /dev/null -w '%{http_code}' http://10.2.7.<prod_ip>:<port>/
# Should return 200
```

### 4.5 Clean Up Old Container

```bash
ssh root@10.2.7.x
pct destroy <old_CTID> --purge
# This frees the LVM volume and removes config
```

---

## Service-Specific Migration Notes

### Media Stack (Docker Compose)

**Container:** CT110 on PVE2 (10.2.7.x)

**Migration pattern:**
- Fresh CT on PVE2 with Debian 12
- Docker + Docker Compose installed fresh
- Docker volumes live on CT rootfs (not on ZFS — Docker-managed volumes are simpler to snapshot via PBS)
- Data volumes bind-mount to `/data` which is a ZFS dataset bind-mounted from the PVE2 host
- Same `docker-compose.yml` and `.env` file copied over
- No service interruption — sync compose file and config dirs, start fresh stack, stop old

**Key commands:**
```bash
# On old CT, stop compose
docker compose -f /opt/pirate-stack/docker-compose.yml down

# Rsync compose file, .env, and config dirs
rsync -av /opt/pirate-stack/ root@PVE2_IP:/opt/pirate-stack/

# On new CT, start
docker compose -f /opt/pirate-stack/docker-compose.yml up -d
```

### Immich (Native — PostgreSQL + Node.js)

**Container:** CT111 on PVE2 (10.2.7.x)

**Migration pattern:**
- Fresh Debian 13 CT with Node.js 24, PostgreSQL 17, Redis
- PostgreSQL database dumped from old CT, restored to new
- App files rsynced (excluding node_modules, upload, cache)
- node_modules rsynced separately (they're architecture-dependent — rsync from old is faster than npm install)
- Photos on ZFS dataset `media/immich_photos`, bind-mounted at `/opt/immich/upload` inside CT
- Permissions: CT UID 999 → host UID 100999

**Key config files:**
- `/opt/immich/.env` — environment variables (DB host, Redis, media location)
- `/etc/systemd/system/immich-web.service` — systemd unit for web service
- `/etc/systemd/system/immich-ml.service` — systemd unit for ML service
- `/opt/immich/app/bin/start.sh` — startup script that loads .env and runs `node dist/main.js`

### Nextcloud (Native — Apache + MariaDB + Redis)

**Container:** CT112 on PVE2 (10.2.7.x)

**Migration pattern:**
- Fresh Debian 12 CT with Apache 2.4, PHP 8.2, MariaDB 10.11, Redis
- MySQL database (nextcloud) dumped from old CT, restored to new
- App files rsynced to `/var/www/nextcloud/`
- User data on ZFS dataset `media/nextcloud_files`, bind-mounted at `/var/www/nextcloud-data`
- Permissions: CT UID 33 (www-data) → host UID 100033

**Key config files:**
- `/var/www/nextcloud/config/config.php` — database credentials, datadirectory path, Redis, memcache
- `/etc/apache2/sites-available/nextcloud.conf` — Apache virtual host
- `/etc/php/8.2/cli/conf.d/nextcloud.ini` — PHP memory limits if customized

**Red flags to watch for:**
- `datadirectory` must point to the ZFS bind mount path inside the CT (e.g., `/var/www/nextcloud-data`)
- The `redis` config section must have proper PHP syntax — broken JSON/SQL quoting can cause parse errors
- MySQL user password must match what's in config.php after restoration
- The `.ncdata` sentinel file must exist in the data directory root

---

## Gitea Update Checklist

After any migration, update this repo:

```bash
cd /tmp/homelab-infra-configs

# Stage changes
git add -A

# Commit with descriptive message
git commit -m "feat: migrate <service> to PVE2 with ZFS storage

- Fresh CT on PVE2 with ZFS bind mount for user data
- Rsynced app files, database, and user content
- Production IP assigned, old container destroyed on PVE1"

# Push
git push
```

---

## Quick Reference: UID Mapping Formula

For unprivileged Proxmox containers:

```
Host UID = Container UID + 100000
```

| To chown files from... | Run this on the HOST |
|------------------------|---------------------|
| `www-data` (UID 33) inside CT | `chown -R 100033:100033 /media/<dataset>` |
| `immich` (UID 999) inside CT | `chown -R 100999:100999 /media/<dataset>` |
| Any user with UID X | `chown -R $((X + 100000)):$((X + 100000)) /media/<dataset>` |

### Migrate Completed Services

| Service | Old CT | New CT | Old PVE | New PVE | New IP | Data Size | ZFS Dataset |
|---------|--------|--------|---------|---------|--------|-----------|-------------|
| Media Stack | CT103 | CT110 | PVE1 | PVE2 | 10.2.7.x | ~530 GB | N/A (Docker volumes) |
| Immich | CT101 | CT111 | PVE1 | PVE2 | 10.2.7.x | 34 GB photos | `media/immich_photos` |
| Nextcloud | CT104 | CT112 | PVE1 | PVE2 | 10.2.7.x | 2.5 GB files | `media/nextcloud_files` |
