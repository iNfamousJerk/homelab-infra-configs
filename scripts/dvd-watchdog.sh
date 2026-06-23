#!/bin/bash
# dvd-watchdog.sh v3 — Runs on PVE2 host
# Polls every 30s for DVD → triggers rip → ejects on completion

LOGFILE="/var/log/dvd-watchdog.log"
CT="103"
DEVICE="/dev/sr0"
RIP_LOG_CT="/var/log/rip-dvd-auto.log"
COOLDOWN_FILE="/tmp/dvd-watchdog-cooldown"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"; }

has_disc()     { timeout 8 isoinfo -d -i "$DEVICE" &>/dev/null; }
disc_volume()  { timeout 6 isoinfo -d -i "$DEVICE" 2>/dev/null | grep "Volume id:" | sed 's/.*: //'; }
rip_running()  { pct exec "$CT" -- pgrep -f "HandBrakeCLI" &>/dev/null; return $?; }

rip_completed_in_log() {
  pct exec "$CT" -- tail -3 "$RIP_LOG_CT" 2>/dev/null | grep -q "✅ Rip complete\|📀 Disc ejected"
}

on_cooldown() {
  [ -f "$COOLDOWN_FILE" ] && [ "$(cat "$COOLDOWN_FILE")" -gt "$(date +%s)" ]
}

set_cooldown() {
  echo "$(($(date +%s) + $1))" > "$COOLDOWN_FILE"
  log "⏳ Cooldown for ${1}s (no eject loop)"
}

eject_disc() {
  log "📀 Ejecting..."
  eject "$DEVICE" 2>/dev/null && log "✅ Ejected" || log "⚠️ Eject failed"
  set_cooldown 120  # don't touch the drive for 2 min
}

start_rip() {
  local title="$1"
  log "📀 Starting rip: $title"
  systemd-run --no-block --unit="rip-$(date +%s)" \
    bash -c "pct exec $CT -- /usr/local/bin/rip-dvd-auto \"$title\"" 2>/dev/null
}

log "=== DVD Watchdog v3 started ==="

was_ripping=0
while true; do
  if has_disc; then
    volume=$(disc_volume)
    
    # Sanitize: replace _ with space, remove numbers at end that look like disc labels
    safe_title=$(echo "$volume" | sed 's/_/ /g; s/  */ /g; s/^ *//; s/ *$//')
    # Remove trailing " - 43" style disc labels
    safe_title=$(echo "$safe_title" | sed 's/ -[0-9][0-9]*$//; s/ [0-9][0-9]*$//')
    # Title-case it
    safe_title=$(echo "$safe_title" | sed 's/\b\(.\)/\u\1/g')
    
    rip_running
    is_rip=$?
    
    if [ "$is_rip" -eq 0 ]; then
      # Rip IS running — track it
      was_ripping=1
      if [ -n "$volume" ]; then
        log "⏳ Ripping: $safe_title"
      fi
    elif [ "$was_ripping" -eq 1 ]; then
      # Rip WAS running but now it's not — it finished!
      log "🎬 Rip completed!"
      was_ripping=0
      sleep 5
      eject_disc
    elif on_cooldown; then
      : # still in cooldown, skip
    elif [ -z "$safe_title" ]; then
      log "📀 Disc detected but no readable title — starting rip anyway"
      start_rip "Untitled_DVD_$(date +%Y%m%d)"
      was_ripping=1
    else
      # Check if movie folder already exists
      if pct exec "$CT" -- test -d "/media/movies/$safe_title" 2>/dev/null; then
        log "📂 $safe_title already exists — skipping"
        eject_disc
      else
        start_rip "$safe_title"
        was_ripping=1
      fi
    fi
  else
    # No disc detected
    if [ "$was_ripping" -eq 1 ]; then
      log "🎬 Rip done (disc ejected/removed)"
      was_ripping=0
    fi
  fi
  
  sleep 30
done