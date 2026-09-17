#!/bin/bash
# Condensed PVE & PBS health check: uptime, updates, CT status, drive stats
# Called by Hermes cron — output delivered to #regular-updates
#
# ── Auth ──────────────────────────────────────────────────────────────
# Key-based SSH only. This script previously carried the root passwords for
# all three hosts in plaintext and ran them through sshpass; those values are
# in git history and must be treated as disclosed.
#
# Setup, once per host:
#
#   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_healthcheck -N ''
#   ssh-copy-id -i ~/.ssh/id_ed25519_healthcheck root@<host>
#
# Recommended hardening — restrict what the key can do. The probe below is
# static, so install it on each host and force it from authorized_keys:
#
#   # on each host, save the probe as /usr/local/sbin/health-probe, then in
#   # /root/.ssh/authorized_keys prefix the key with:
#   restrict,from="<hermes-ip>",command="/usr/local/sbin/health-probe" ssh-ed25519 AAAA...
#
# With a forced command the key cannot be used for an interactive shell even
# if it leaks. Print the probe to install with:  PRINT_PROBE=1 ./this-script
#
# ── Config ────────────────────────────────────────────────────────────
# Required:  PVE1_HOST, PVE2_HOST, PBS_HOST
# Optional:  HEALTHCHECK_SSH_KEY  (default ~/.ssh/id_ed25519_healthcheck)
#            HEALTHCHECK_SSH_USER (default root)
#            SSH_STRICT           (default accept-new)
set -euo pipefail

SSH_USER="${HEALTHCHECK_SSH_USER:-root}"
SSH_KEY="${HEALTHCHECK_SSH_KEY:-$HOME/.ssh/id_ed25519_healthcheck}"

# accept-new pins a host key on first contact and refuses it if it later
# changes. The previous `no` accepted any key every time, which is no
# protection against a machine-in-the-middle on the management VLAN.
SSH_OPTS=(
  -o BatchMode=yes
  -o StrictHostKeyChecking="${SSH_STRICT:-accept-new}"
  -o ConnectTimeout=10
  -i "$SSH_KEY"
)

# ── Remote probes ─────────────────────────────────────────────────────
# Delivered over stdin to `bash -s`, so nothing here is expanded locally and
# inner quoting stays readable (the old version passed these as a single
# quoted argument and had to escape every awk field reference as \$2).
#
# Deliberately no `set -e` on the remote side: a probe is best-effort, and a
# missing tool should blank one section rather than truncate the report.

read -r -d '' PROBE_COMMON <<'PROBE' || true
echo "===UPDATES==="
apt update -qq 2>/dev/null
apt list --upgradable 2>/dev/null | grep -c upgradable
echo "REBOOTREQ"
[ -f /var/run/reboot-required ] && echo "YES" || echo "NO"
echo "===UPTIME==="
uptime -p | sed 's/^up //'
echo "===LOAD==="
uptime | awk -F'load average:' '{print $2}' | xargs
echo "===MEM==="
free -h | grep Mem | awk '{print $3"/"$2" used"}'
echo "===DISK-ROOT==="
df -h / | tail -1 | awk '{print $3"/"$2" ("$5")"}'
PROBE

read -r -d '' PROBE_CTS <<'PROBE' || true
echo "===CTS==="
for vmid in $(pct list 2>/dev/null | tail -n +2 | awk '{print $1}'); do
  status=$(pct status "$vmid" 2>/dev/null | awk '{print $2}')
  hostname=$(pct exec "$vmid" -- hostname 2>/dev/null || echo "?")
  echo "$vmid $status $hostname"
done
PROBE

read -r -d '' PROBE_PVE_VERSION <<'PROBE' || true
echo "===VERSION==="
dpkg -s pve-manager 2>/dev/null | grep "^Version:" | cut -d" " -f2 || echo "unknown"
PROBE

# Emits one "<dev> <size> <PASSED|FAILED|?> <model...>" line per disk.
# Unquoted heredoc: $section and $devices expand here, while \$d and friends
# are escaped so they survive to be expanded remotely.
probe_disks() {
  local section="$1" devices="$2"
  cat <<PROBE
echo "===${section}==="
for d in ${devices}; do
  model=\$(lsblk -ndo MODEL /dev/\$d 2>/dev/null | head -1)
  size=\$(lsblk -ndo SIZE /dev/\$d 2>/dev/null | head -1)
  smart=\$(smartctl -H /dev/\$d 2>/dev/null | grep -m1 "PASSED\|FAILED" | grep -o "PASSED\|FAILED" || echo "?")
  echo "\$d \$size \$smart \$model"
done
PROBE
}

read -r -d '' PROBE_ZPOOL <<'PROBE' || true
echo "===ZPOOL==="
zpool list -H -o name,size,alloc,capacity,health 2>/dev/null | head -1
PROBE

# PVE1: single LVM-backed system disk
read -r -d '' PROBE_PVE_EXTRA <<'PROBE' || true
echo "===DISK-MODEL==="
lsblk -ndo MODEL /dev/sda 2>/dev/null | head -1
echo "===DISK-SIZE==="
lsblk -ndo SIZE /dev/sda 2>/dev/null | head -1
echo "===SMART==="
smartctl -H /dev/sda 2>/dev/null | grep -o "PASSED\|FAILED" || echo "N/A"
echo "===LV-DETAIL==="
lvs --noheadings -o lv_name,lv_size,data_percent 2>/dev/null | awk '{if ($3 != "") print $1,$2,$3"%"; else print $1,$2,"-"}'
PROBE

# PBS: version string comes from proxmox-backup-manager, plus datastore usage
read -r -d '' PROBE_PBS_EXTRA <<'PROBE' || true
echo "===VERSION==="
proxmox-backup-manager versions --verbose 2>/dev/null | grep "proxmox-backup-server" | awk '{print $2}' || echo "(unknown)"
PROBE

read -r -d '' PROBE_PBS_DATASTORE <<'PROBE' || true
echo "===DATASTORE==="
proxmox-backup-manager datastore list 2>/dev/null | grep -A4 "main"
PROBE

# PVE2: boots off sde, data on a 4-disk ZFS pool
read -r -d '' PROBE_PVE2_BOOT <<'PROBE' || true
echo "===BOOT-DISK==="
lsblk -ndo MODEL /dev/sde 2>/dev/null | head -1
PROBE

PROBE_PVE="${PROBE_COMMON}
${PROBE_PVE_VERSION}
${PROBE_PVE_EXTRA}
${PROBE_CTS}"

PROBE_PBS="${PROBE_COMMON}
${PROBE_PBS_EXTRA}
${PROBE_ZPOOL}
$(probe_disks DISKS 'sda sdb sdc')
${PROBE_PBS_DATASTORE}"

PROBE_PVE2="${PROBE_COMMON}
${PROBE_PVE_VERSION}
${PROBE_PVE2_BOOT}
${PROBE_ZPOOL}
$(probe_disks ZPOOL-DISKS 'sda sdb sdc sdd')
${PROBE_CTS}"

if [ "${PRINT_PROBE:-0}" = "1" ]; then
  printf '### PVE1 probe\n%s\n\n### PBS probe\n%s\n\n### PVE2 probe\n%s\n' \
    "$PROBE_PVE" "$PROBE_PBS" "$PROBE_PVE2"
  exit 0
fi

PVE1_HOST="${PVE1_HOST:?set PVE1_HOST (see header)}"
PVE2_HOST="${PVE2_HOST:?set PVE2_HOST (see header)}"
PBS_HOST="${PBS_HOST:?set PBS_HOST (see header)}"

# ── Collection ────────────────────────────────────────────────────────
ERR_FILE="$(mktemp)"
trap 'rm -f "$ERR_FILE"' EXIT

# Sets <prefix>_raw / <prefix>_exit / <prefix>_err. stderr is captured
# separately rather than folded in with 2>&1, which used to let ssh warnings
# land in the parsed output and corrupt whichever section they interrupted.
collect() {
  local prefix="$1" host="$2" script="$3" out
  if out="$(ssh "${SSH_OPTS[@]}" "${SSH_USER}@${host}" bash -s <<<"$script" 2>"$ERR_FILE")"; then
    printf -v "${prefix}_raw" '%s' "$out"
    eval "${prefix}_exit=0"
    eval "${prefix}_err=''"
  else
    local rc=$?
    eval "${prefix}_raw=''"
    eval "${prefix}_exit=$rc"
    printf -v "${prefix}_err" '%s' "$(head -3 "$ERR_FILE" | tr '\n' ' ' | sed 's/ *$//')"
  fi
}

collect pve  "$PVE1_HOST"  "$PROBE_PVE"
collect pbs  "$PBS_HOST"  "$PROBE_PBS"
collect pve2 "$PVE2_HOST" "$PROBE_PVE2"

# ── Parse helpers ─────────────────────────────────────────────────────
extract_line_after() {
  sed -n "/^$2$/{n;p}" <<<"$1"
}
extract_block() {
  sed -n "/^$2$/,/^$3$/{/^$2$/d;/^$3$/d;p}" <<<"$1"
}

# ── Render helpers ────────────────────────────────────────────────────
# One copy each of what used to be three near-identical blocks.
render_header() {
  local icon="$1" label="$2" host="$3" raw="$4"
  echo "**${icon} ${label} — ${host}**  |  up $(extract_line_after "$raw" '===UPTIME===')"
  echo "  \`v$(extract_line_after "$raw" '===VERSION===')\`  |  Load: $(extract_line_after "$raw" '===LOAD===')  |  Mem: $(extract_line_after "$raw" '===MEM===')"
}

render_zpool() {
  local raw="$1" label="$2" line name size alloc cap health
  line="$(extract_line_after "$raw" '===ZPOOL===')"
  [ -n "$line" ] || return 0
  read -r name size alloc cap health _ <<<"$line"
  echo "  **🗄️ ${label}:** ${name}  |  ${size} total, ${alloc} used (${cap})  |  **${health}**"
}

render_disks() {
  # A 4th read variable soaks up the remaining fields, so multi-word disk
  # models survive without the awk field loop this used to need.
  local disks="$1" disk name size smart model icon
  while IFS= read -r disk; do
    [ -n "$disk" ] || continue
    read -r name size smart model <<<"$disk"
    icon="✅"; [ "$smart" = "PASSED" ] || icon="⚠️"
    echo "    ${icon} /dev/${name}  ${size}  —  ${model}"
  done <<<"$disks"
}

render_cts() {
  local cts="$1" total running stopped vmid status name
  total="$(grep -c '.' <<<"$cts" || true)"
  running="$(awk '$2 == "running"' <<<"$cts" | wc -l)"
  stopped="$(awk '$2 == "stopped"' <<<"$cts" | wc -l)"
  echo "  **📦 Containers:** ${total} total  |  🟢 ${running} running  |  🔴 ${stopped} stopped"
  while IFS= read -r ct; do
    [ -n "$ct" ] || continue
    read -r vmid status name _ <<<"$ct"
    if [ "$status" = "running" ]; then
      echo "    🟢 $vmid ($name)"
    else
      echo "    🔴 $vmid ($name)"
    fi
  done <<<"$cts"
}

render_updates() {
  local raw="$1" count reboot
  count="$(extract_block "$raw" '===UPDATES===' 'REBOOTREQ' | head -1)"
  reboot="$(extract_line_after "$raw" 'REBOOTREQ')"
  if [ "${count:-0}" -gt 0 ] 2>/dev/null; then
    echo "  🔄 **$count** updates available"
  else
    echo "  ✅ All packages up to date"
  fi
  if [ "$reboot" = "YES" ]; then
    echo "  ⚠️  **Reboot required** (kernel updated)"
  fi
}

render_failure() {
  local icon="$1" label="$2" host="$3" err="$4"
  echo "**🔴 ${label} — ${host}** — SSH connection failed"
  [ -z "$err" ] || echo "  \`${err}\`"
}

separator() {
  echo
  echo "━━━━━━━━━━━━━━━"
  echo
}

# ── Output ────────────────────────────────────────────────────────────
echo "**📡 Health Check — $(date '+%a %b %d %Y %I:%M %p')**"
echo

# PVE1 — LVM system disk + containers
if [ "$pve_exit" -eq 0 ]; then
  render_header "🖥️" PVE "$PVE1_HOST" "$pve_raw"
  echo
  echo "  **💾 Drive:** $(extract_line_after "$pve_raw" '===DISK-MODEL===') ($(extract_line_after "$pve_raw" '===DISK-SIZE==='))  |  SMART: $(extract_line_after "$pve_raw" '===SMART===')  |  $(extract_line_after "$pve_raw" '===DISK-ROOT===')"
  while IFS= read -r lv; do
    [ -n "$lv" ] || continue
    read -r lv_name lv_size lv_pct _ <<<"$lv"
    if [ "$lv_pct" != "-" ]; then
      echo "    └─ $lv_name  ${lv_size}  (${lv_pct})"
    else
      echo "    └─ $lv_name  ${lv_size}"
    fi
  done <<<"$(extract_block "$pve_raw" '===LV-DETAIL===' '===CTS===' | grep -v '^$' || true)"
  echo
  render_cts "$(extract_block "$pve_raw" '===CTS===' '' | grep -v '^$' || true)"
  echo
  render_updates "$pve_raw"
else
  render_failure "🖥️" PVE "$PVE1_HOST" "$pve_err"
fi

separator

# PBS — ZFS pool + per-disk SMART
if [ "$pbs_exit" -eq 0 ]; then
  render_header "💾" PBS "$PBS_HOST" "$pbs_raw"
  echo
  render_zpool "$pbs_raw" "ZFS Pool"
  echo
  echo "  **💽 Drives:**"
  render_disks "$(extract_block "$pbs_raw" '===DISKS===' '===DATASTORE===' | grep -v '^$' || true)"
  echo "  OS: $(extract_line_after "$pbs_raw" '===DISK-ROOT===')"
  echo
  render_updates "$pbs_raw"
else
  render_failure "💾" PBS "$PBS_HOST" "$pbs_err"
fi

separator

# PVE2 — boot disk + ZFS pool + containers
if [ "$pve2_exit" -eq 0 ]; then
  render_header "🖥️" PVE2 "$PVE2_HOST" "$pve2_raw"
  echo
  echo "  **💾 Boot:** $(extract_line_after "$pve2_raw" '===BOOT-DISK===')  |  $(extract_line_after "$pve2_raw" '===DISK-ROOT===')"
  render_zpool "$pve2_raw" "ZFS"
  echo
  echo "  **💽 Pool Drives:**"
  render_disks "$(extract_block "$pve2_raw" '===ZPOOL-DISKS===' '===CTS===' | grep -v '^$' || true)"
  echo
  render_cts "$(extract_block "$pve2_raw" '===CTS===' '' | grep -v '^$' || true)"
  echo
  render_updates "$pve2_raw"
else
  render_failure "🖥️" PVE2 "$PVE2_HOST" "$pve2_err"
fi

exit 0
