#!/usr/bin/env python3
"""Piper Homelab — Control Panel v3 with Tab Navigation, Updated Services & Architecture"""
import re, os, time, json, urllib.request, ssl
from flask import Flask, render_template_string

app = Flask(__name__)

stats_cache = {"data": None, "time": 0}
CACHE_TTL = 60

SERVICES = [
    {"name": "Jellyfin", "url": "http://10.2.7.x:8096", "icon": "🎬", "cat": "media"},
    {"name": "Radarr", "url": "http://10.2.7.x:7878", "icon": "🎥", "cat": "arr"},
    {"name": "Sonarr", "url": "http://10.2.7.x:8989", "icon": "📺", "cat": "arr"},
    {"name": "Lidarr", "url": "http://10.2.7.x:8686", "icon": "🎵", "cat": "arr"},
    {"name": "Readarr", "url": "http://10.2.7.x:8787", "icon": "📖", "cat": "arr"},
    {"name": "Prowlarr", "url": "http://10.2.7.x:9696", "icon": "🔍", "cat": "arr"},
    {"name": "Bazarr", "url": "http://10.2.7.x:6767", "icon": "💬", "cat": "arr"},
    {"name": "qBittorrent", "url": "http://10.2.7.x:8080", "icon": "⚡", "cat": "download"},
    {"name": "Navidrome", "url": "http://10.2.7.x:4533", "icon": "🎶", "cat": "media"},
    {"name": "Audiobookshelf", "url": "http://10.2.7.x:13378", "icon": "🎧", "cat": "media"},
    {"name": "Requestrr", "url": "http://10.2.7.x:4545", "icon": "📝", "cat": "request"},
    {"name": "Immich", "url": "http://10.2.7.x:2283", "icon": "📸", "cat": "media"},
    {"name": "Nextcloud", "url": "http://10.2.7.x", "icon": "☁️", "cat": "infra"},
    {"name": "NPM", "url": "http://10.2.7.x:81", "icon": "🔒", "cat": "infra"},
    {"name": "Grafana", "url": "http://10.2.7.x:3000", "icon": "📊", "cat": "monitor"},
    {"name": "Uptime Kuma", "url": "http://10.2.7.x:3001", "icon": "❤️", "cat": "monitor"},
    {"name": "Wazuh", "url": "https://10.2.7.x:443", "icon": "🛡️", "cat": "security"},
    {"name": "Pi-hole", "url": "http://10.2.7.x/admin", "icon": "🚫", "cat": "network"},
    {"name": "Gitea", "url": "http://10.2.7.x:3002", "icon": "🔧", "cat": "dev"},
    {"name": "Portainer", "url": "https://10.2.7.x:9443", "icon": "🐳", "cat": "infra"},
    {"name": "Cockpit", "url": "https://10.2.7.x:9090", "icon": "🖥️", "cat": "infra"},
    {"name": "HO (Ollama)", "url": "http://10.2.7.x:11434", "icon": "🧠", "cat": "ai"},
    {"name": "DVD Ripper", "url": "http://10.2.7.x:5050", "icon": "💿", "cat": "tools"},
    {"name": "Media Dash", "url": "http://10.2.7.x:5051", "icon": "📋", "cat": "tools"},
    {"name": "Homelab Panel", "url": "http://10.2.7.x:5052", "icon": "🏗️", "cat": "docs"},
]

PVE_PASSWORDS = {
    "10.2.7.x": "2proxtheworld",
    "10.2.7.x": "2proxtheworld",
    "10.2.7.x": "2backuptheworld",
}

def pve_api(host, endpoint, password):
    """Authenticate to Proxmox API and fetch endpoint data."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    base = f"https://{host}:8006/api2/json"
    try:
        auth_data = urllib.parse.urlencode({"username": "root@pam", "password": password}).encode()
        req = urllib.request.Request(f"{base}/access/ticket", data=auth_data, method="POST")
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        ticket_data = json.loads(resp.read())
        ticket = ticket_data["data"]["ticket"]
        csrf = ticket_data["data"]["CSRFPreventionToken"]
        req2 = urllib.request.Request(f"{base}{endpoint}")
        req2.add_header("Cookie", f"PVEAuthCookie={ticket}")
        req2.add_header("CSRFPreventionToken", csrf)
        resp2 = urllib.request.urlopen(req2, context=ctx, timeout=10)
        return json.loads(resp2.read())["data"]
    except Exception as e:
        return {"error": str(e)}

def parse_node_status(host, label, password):
    """Get node status via Proxmox API."""
    s = {"host": host, "label": label}
    status_data = pve_api(host, "/nodes/localhost/status", password)
    if isinstance(status_data, dict) and "error" in status_data:
        s["error"] = status_data["error"]
        return s
    if isinstance(status_data, dict):
        s["uptime"] = f"{status_data.get('uptime', 0) / 86400:.0f}d {(status_data.get('uptime', 0) % 86400) / 3600:.0f}h" if status_data.get("uptime") else "—"
        s["load"] = " ".join(str(x) for x in status_data.get("loadavg", [])) if status_data.get("loadavg") else "—"
        mem_total = status_data.get("memory", {}).get("total", 0)
        mem_used = status_data.get("memory", {}).get("used", 0)
        if mem_total:
            s["mem_total"] = f"{mem_total / 1073741824:.1f}Gi" if mem_total > 1e9 else f"{mem_total / 1048576:.0f}Mi"
            s["mem_used"] = f"{mem_used / 1073741824:.1f}Gi" if mem_used > 1e9 else f"{mem_used / 1048576:.0f}Mi"
        rootfs = status_data.get("rootfs", {})
        if isinstance(rootfs, dict):
            total = rootfs.get("total", 0)
            used = rootfs.get("used", 0)
            if total:
                pct = round(used / total * 100)
                s["disk_total"] = f"{total / 1073741824:.0f}G" if total > 1e9 else f"{total / 1048576:.0f}M"
                s["disk_used"] = f"{used / 1073741824:.0f}G" if used > 1e9 else f"{used / 1048576:.0f}M"
                s["disk_pct"] = f"{pct}%"
                if pct < 70: s["disk_bar"] = "green"
                elif pct < 90: s["disk_bar"] = "yellow"
                else: s["disk_bar"] = "red"
        if isinstance(status_data.get("cpuinfo"), dict):
            ci = status_data["cpuinfo"]
            if not s.get("cpu"): s["cpu"] = ci.get("model", "—").strip()
            if not s.get("cores"): s["cores"] = ci.get("cpus", "—")
        cpuinfo = pve_api(host, "/nodes/localhost/hardware/cpu", password)
        if isinstance(cpuinfo, list) and len(cpuinfo) > 0:
            s["cpu"] = cpuinfo[0].get("model", "").strip()
        ct_data = pve_api(host, "/nodes/localhost/lxc", password)
        cts = []
        if isinstance(ct_data, list):
            for r in ct_data:
                cts.append(f"{r.get('vmid','?')} | {r.get('name','?')} | {r.get('status','?')}")
        elif isinstance(ct_data, dict) and "error" not in ct_data:
            pass
        s["cts"] = cts
    return s

def parse_pbs_status(host, label, password):
    """Get PBS status via Proxmox Backup Server API."""
    s = {"host": host, "label": label}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    base = f"https://{host}:8007/api2/json"
    try:
        auth_data = urllib.parse.urlencode({"username": "root@pam", "password": password}).encode()
        req = urllib.request.Request(f"{base}/access/ticket", data=auth_data, method="POST")
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        ticket_data = json.loads(resp.read())
        ticket = ticket_data["data"]["ticket"]
        def pbs_get(path):
            r = urllib.request.Request(f"{base}{path}")
            r.add_header("Cookie", f"PBSAuthCookie={ticket}")
            return json.loads(urllib.request.urlopen(r, context=ctx, timeout=10).read())["data"]
        version_data = pbs_get("/version")
        if isinstance(version_data, dict):
            s["version"] = version_data.get("version", "—")
        try:
            ns = pbs_get("/nodes/localhost/status")
            if isinstance(ns, dict):
                if isinstance(ns.get("cpuinfo"), dict):
                    s["cpu"] = ns["cpuinfo"].get("model", "—")
                    s["cores"] = ns["cpuinfo"].get("cpus", "—")
                mem = ns.get("memory", {})
                if mem.get("total"):
                    s["mem_total"] = f"{mem['total'] / 1073741824:.1f}Gi"
                    s["mem_used"] = f"{mem['used'] / 1073741824:.1f}Gi"
                if ns.get("loadavg"):
                    s["load"] = " ".join(str(x) for x in ns["loadavg"])
                if ns.get("uptime"):
                    upt = ns["uptime"]
                    s["uptime"] = f"{upt // 86400:.0f}d {(upt % 86400) // 3600:.0f}h"
                root = ns.get("root", {})
                if root.get("total"):
                    total = root["total"]
                    used = root.get("used", 0)
                    pct = round(used / total * 100)
                    s["boot_total"] = f"{total / 1073741824:.0f}G"
                    s["boot_used"] = f"{used / 1073741824:.0f}G"
                    s["boot_pct"] = f"{pct}%"
        except:
            pass
        s["datastores"] = []
        ds_list = pbs_get("/admin/datastore")
        if isinstance(ds_list, list):
            for d in ds_list:
                store_name = d.get("store")
                if store_name:
                    try:
                        ds_status = pbs_get(f"/admin/datastore/{store_name}/status")
                        if isinstance(ds_status, dict):
                            total = ds_status.get("total", 0)
                            used = ds_status.get("used", 0)
                            if total:
                                pct = round(used / total * 100)
                                s["datastores"].append({
                                    "name": store_name,
                                    "total": f"{total / 1099511627776:.1f}T" if total > 1e12 else f"{total / 1073741824:.0f}G",
                                    "used": f"{used / 1099511627776:.1f}T" if used > 1e12 else f"{used / 1073741824:.0f}G",
                                    "pct": f"{pct}%",
                                    "bar": "green" if pct < 70 else "yellow" if pct < 90 else "red"
                                })
                    except:
                        pass
        if s.get("datastores"):
            s["disk_total"] = s["datastores"][0]["total"]
            s["disk_used"] = s["datastores"][0]["used"]
            s["disk_pct"] = s["datastores"][0]["pct"]
    except Exception as e:
        s["error"] = str(e)
    return s

def collect_stats():
    pve1 = parse_node_status("10.2.7.x", "PVE1", PVE_PASSWORDS.get("10.2.7.x", ""))
    pve2 = parse_node_status("10.2.7.x", "PVE2", PVE_PASSWORDS.get("10.2.7.x", ""))
    pbs = parse_pbs_status("10.2.7.x", "PBS", PVE_PASSWORDS.get("10.2.7.x", ""))
    return {"pve1": pve1, "pve2": pve2, "pbs": pbs}

# ─── Architecture SVG ───────────────────────────────────────────
ARCH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 870" style="background:#020617;width:100%;height:auto;max-width:1100px">
<style>
text{font-family:system-ui,-apple-system,sans-serif;fill:#e2e8f0;font-size:11px}
.box{fill:rgba(15,23,42,0.8);stroke:#1e293b;stroke-width:1.5;rx:6;ry:6}
.box2{fill:rgba(30,41,59,0.6);stroke:#334155;stroke-width:1;rx:4;ry:4}
.box3{fill:rgba(15,23,42,0.5);stroke:#a78bfa;stroke-width:1;rx:4;ry:4}
.label{font-size:10px;fill:#94a3b8}
.hl{fill:#22d3ee;font-weight:bold}
.arr{fill:#fbbf24}
.media{fill:#22d3ee}
.mon{fill:#34d399}
.sec{fill:#fb7185}
.infra{fill:#a78bfa}
.net{fill:#fb923c}
.ai{fill:#c084fc}
.line{stroke:#334155;stroke-width:1.5;fill:none}
.title{font-size:13px;font-weight:bold;fill:#f1f5f9}
.sub{font-size:10px;fill:#64748b}
</style>
<!-- Title -->
<text x="550" y="30" text-anchor="middle" class="title">🏠 Piper Homelab Topology</text>
<text x="550" y="46" text-anchor="middle" class="sub">Las Vegas · 10.2.7.x/24 · Proxmox Cluster</text>
<!-- === INTERNET === -->
<rect x="450" y="60" width="200" height="36" class="box"/>
<text x="550" y="77" text-anchor="middle" font-size="12" fill="#34d399">🌐 Internet</text>
<text x="550" y="90" text-anchor="middle" class="label">Comcast Cable</text>
<line x1="550" y1="96" x2="550" y2="118" class="line"/>
<!-- === OPNsense === -->
<rect x="400" y="120" width="300" height="44" class="box" stroke="#fb923c"/>
<text x="550" y="140" text-anchor="middle" font-size="12" class="net">🛡 OPNsense</text>
<text x="550" y="155" text-anchor="middle" class="label">VLANs: Family (10.2.10.1) · Server (10.2.30.1) · Guest (10.2.20.1) · LAN (10.2.7.x)</text>
<line x1="550" y1="164" x2="550" y2="182" class="line"/>
<!-- === Switch === -->
<rect x="400" y="184" width="300" height="36" class="box" stroke="#34d399"/>
<text x="550" y="200" text-anchor="middle" font-size="12" class="mon">🔀 NETGEAR GS305E</text>
<text x="550" y="214" text-anchor="middle" class="label">Managed Gigabit Switch</text>
<line x1="220" y1="220" x2="220" y2="250" class="line"/>
<line x1="550" y1="220" x2="550" y2="250" class="line"/>
<line x1="880" y1="220" x2="880" y2="250" class="line"/>
<!-- === PVE1 === -->
<rect x="120" y="252" width="200" height="36" class="box" stroke="#22d3ee"/>
<text x="220" y="269" text-anchor="middle" font-size="12" class="hl">🖥 PVE1 — 10.2.7.x</text>
<text x="220" y="282" text-anchor="middle" class="label">i5-7500 · 31GB RAM · 94GB SSD</text>
<rect x="95" y="295" width="250" height="310" class="box2"/>
<text x="220" y="312" text-anchor="middle" class="label" font-size="9">CONTAINERS</text>
<rect x="105" y="320" width="110" height="34" class="box3"/><text x="160" y="335" text-anchor="middle" font-size="10" class="infra">🤖 Hermes (100)</text><text x="160" y="348" text-anchor="middle" class="label">AI Agent · 10.2.7.x</text>
<rect x="225" y="320" width="110" height="34" class="box3"/><text x="280" y="335" text-anchor="middle" font-size="10" class="sec">⚠ PiAlert (102)</text><text x="280" y="348" text-anchor="middle" class="label">Network Alerts</text>
<rect x="105" y="360" width="110" height="34" class="box3"/><text x="160" y="375" text-anchor="middle" font-size="10" class="sec">🛡 Wazuh (105)</text><text x="160" y="388" text-anchor="middle" class="label">SIEM · 10.2.7.x</text>
<rect x="225" y="360" width="110" height="34" class="box3"/><text x="280" y="375" text-anchor="middle" font-size="10" class="mon">📊 Grafana (106)</text><text x="280" y="388" text-anchor="middle" class="label">Monitoring · 10.2.7.x</text>
<rect x="105" y="400" width="110" height="34" class="box3"/><text x="160" y="415" text-anchor="middle" font-size="10" class="net">🚫 Pi-hole (107)</text><text x="160" y="428" text-anchor="middle" class="label">DNS · 10.2.7.x</text>
<rect x="225" y="400" width="110" height="34" class="box3"/><text x="280" y="415" text-anchor="middle" font-size="10" class="infra">🐳 Portainer (108)</text><text x="280" y="428" text-anchor="middle" class="label">Docker Mgr · 10.2.7.x</text>
<rect x="105" y="440" width="110" height="34" class="box3"/><text x="160" y="455" text-anchor="middle" font-size="10" class="infra">📋 Heimdall (109)</text><text x="160" y="468" text-anchor="middle" class="label">Dashboard · 10.2.7.x</text>
<rect x="225" y="440" width="110" height="34" class="box3"/><text x="280" y="455" text-anchor="middle" font-size="10" class="mon">❤️ Uptime Kuma</text><text x="280" y="468" text-anchor="middle" class="label">Monitor · 10.2.7.x:3001</text>
<rect x="105" y="480" width="110" height="34" class="box3"/><text x="160" y="495" text-anchor="middle" font-size="10" class="ai">🧠 HO (113)</text><text x="160" y="508" text-anchor="middle" class="label">Ollama · 10.2.7.x</text>
<rect x="225" y="480" width="110" height="34" class="box3"/><text x="280" y="495" text-anchor="middle" font-size="10" class="infra">🖥️ Cockpit (114)</text><text x="280" y="508" text-anchor="middle" class="label">Web Admin · 10.2.7.x</text>
<text x="220" y="590" text-anchor="middle" class="label">🔗 VLAN: Server (10.2.30.1)</text>
<!-- === PVE2 === -->
<rect x="450" y="252" width="200" height="36" class="box" stroke="#22d3ee"/>
<text x="550" y="269" text-anchor="middle" font-size="12" class="hl">🖥 PVE2 — 10.2.7.x</text>
<text x="550" y="282" text-anchor="middle" class="label">i7-2600 · 16GB RAM · 2.72TB ZFS</text>
<rect x="425" y="295" width="250" height="245" class="box2"/>
<text x="550" y="312" text-anchor="middle" class="label" font-size="9">CONTAINERS</text>
<rect x="435" y="320" width="110" height="34" class="box3"/><text x="490" y="335" text-anchor="middle" font-size="10" class="sec">🔍 Zeek (101)</text><text x="490" y="348" text-anchor="middle" class="label">IDS Sensor</text>
<rect x="555" y="320" width="110" height="34" class="box3"/><text x="610" y="335" text-anchor="middle" font-size="10" class="tools">💿 Ripper (103)</text><text x="610" y="348" text-anchor="middle" class="label">DVD Ripping</text>
<rect x="435" y="360" width="150" height="34" class="box3"/><text x="510" y="375" text-anchor="middle" font-size="10" class="media">🎬 Media Stack (110)</text><text x="510" y="388" text-anchor="middle" class="label">Jellyfin + *arrs</text>
<rect x="435" y="400" width="110" height="34" class="box3"/><text x="490" y="415" text-anchor="middle" font-size="10" class="media">📸 Immich (111)</text><text x="490" y="428" text-anchor="middle" class="label">Photo Backup · 10.2.7.x</text>
<rect x="555" y="400" width="110" height="34" class="box3"/><text x="610" y="415" text-anchor="middle" font-size="10" class="infra">☁ Nextcloud (112)</text><text x="610" y="428" text-anchor="middle" class="label">File Sync · 10.2.7.x</text>
<text x="550" y="530" text-anchor="middle" class="label">🔗 VLAN: Server (10.2.30.1) · ZFS: media pool</text>
<!-- === PBS === -->
<rect x="780" y="252" width="200" height="36" class="box" stroke="#a78bfa"/>
<text x="880" y="269" text-anchor="middle" font-size="12" class="infra">💾 PBS — 10.2.7.x</text>
<text x="880" y="282" text-anchor="middle" class="label">Xeon E3-1225 v3 · 15GB · 3TB</text>
<rect x="760" y="295" width="240" height="100" class="box2"/>
<text x="880" y="315" text-anchor="middle" class="label" font-size="9">BACKUP SERVER</text>
<text x="790" y="340" class="label">• Backs up all CTs</text>
<text x="790" y="358" class="label">• Media backups via cron</text>
<text x="790" y="376" class="label">• Datastore: media-backups</text>
<rect x="760" y="405" width="240" height="75" class="box2" stroke="#34d399"/>
<text x="880" y="425" text-anchor="middle" class="label" font-size="9">BACKUP SCHEDULE</text>
<text x="790" y="445" class="net">✓ All CTs: daily @ 03:30, 15:30</text>
<text x="790" y="463" class="net">✓ Media stack: 33 min past</text>
<!-- === Bottom sections === -->
<rect x="200" y="560" width="700" height="44" class="box" stroke="#fbbf24"/>
<text x="550" y="578" text-anchor="middle" font-size="12" class="arr">📺 Media Stack — CT 110 (10.2.7.x)</text>
<text x="550" y="594" text-anchor="middle" class="label">🎬 Jellyfin :8096 · 🎥 Radarr :7878 · 📺 Sonarr :8989 · 🔍 Prowlarr :9696 · ⚡ qBit :8080 · 🎶 Navidrome :4533</text>
<rect x="200" y="620" width="700" height="44" class="box" stroke="#34d399"/>
<text x="550" y="640" text-anchor="middle" font-size="12" class="mon">💾 Storage Layout</text>
<text x="550" y="656" text-anchor="middle" class="label">PVE1: 94GB SSD (boot) · PVE2: 2TB+1TB ZFS mirror (@ /media/data) · PBS: 3TB Hitachi @ media-backups</text>
<rect x="200" y="680" width="700" height="30" class="box" stroke="#fb923c"/>
<text x="550" y="700" text-anchor="middle" class="label" font-size="11">📁 SMB: \\\\10.2.7.x\\Media · \\\\10.2.7.x\\Immich · \\\\10.2.7.x\\Nextcloud — user: media/media</text>
<rect x="200" y="725" width="700" height="50" class="box2"/>
<text x="230" y="742" class="label" font-size="9">Legend:</text>
<rect x="290" y="733" width="10" height="10" rx="2" fill="#22d3ee"/><text x="305" y="742" font-size="9" fill="#22d3ee">Proxmox</text>
<rect x="380" y="733" width="10" height="10" rx="2" fill="#fbbf24"/><text x="395" y="742" font-size="9" fill="#fbbf24">Media</text>
<rect x="455" y="733" width="10" height="10" rx="2" fill="#34d399"/><text x="470" y="742" font-size="9" fill="#34d399">Infra</text>
<rect x="530" y="733" width="10" height="10" rx="2" fill="#fb7185"/><text x="545" y="742" font-size="9" fill="#fb7185">Security</text>
<rect x="620" y="733" width="10" height="10" rx="2" fill="#fb923c"/><text x="635" y="742" font-size="9" fill="#fb923c">Network</text>
<rect x="710" y="733" width="10" height="10" rx="2" fill="#a78bfa"/><text x="725" y="742" font-size="9" fill="#a78bfa">Backup</text>
<rect x="790" y="733" width="10" height="10" rx="2" fill="#c084fc"/><text x="805" y="742" font-size="9" fill="#c084fc">AI</text>
<text x="550" y="768" text-anchor="middle" class="sub" font-size="9">Generated by Hermes Agent · v3 · Updated Jul 2026</text>
</svg>"""

# ─── HTML Template v3 — Tab Buttons + Mauve Dark Theme ──────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Piper Homelab</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}

body{
  font-family:'Inter',system-ui,-apple-system,sans-serif;
  background:#C48B9F;
  color:#fff;
  min-height:100vh;
  overflow-x:hidden;
}

.container{max-width:1100px;margin:0 auto;padding:0.75rem}

/* ── Header ── */
.header{
  background:#121212;
  border-radius:14px;
  padding:0.9rem 1.25rem;
  margin-bottom:0.75rem;
  border:1px solid #2a2a2a;
}
.header-row{display:flex;align-items:center;justify-content:space-between}
.header-left{display:flex;align-items:center;gap:0.75rem}
.header-icon{font-size:1.4rem}
h1{font-size:1.15rem;font-weight:700;letter-spacing:-0.02em}
.header-right{text-align:right}
.last-update{color:#888;font-size:0.65rem;line-height:1.3}
.status-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#34d399;margin-right:4px}
.subtitle{color:#999;font-size:0.72rem;margin-top:2px}

/* ── Tab Navigation ── */
.tab-bar{
  display:flex;gap:0;margin-bottom:0.75rem;
  background:#121212;border-radius:10px;border:1px solid #2a2a2a;
  overflow:hidden;
}
.tab-btn{
  flex:1;text-align:center;
  padding:0.6rem 0.5rem;cursor:pointer;font-size:0.78rem;font-weight:500;
  color:#666;transition:all 0.2s;
  border:none;background:transparent;font-family:inherit;
}
.tab-btn.active{color:#fff;background:rgba(255,255,255,0.06)}
.tab-btn:not(:last-child){border-right:1px solid #2a2a2a}

/* ── Tab Content ── */
.tab-content{display:none}
.tab-content.active{display:block}

/* ── Cards ── */
.card{
  background:#121212;
  border-radius:14px;
  padding:0.9rem 1rem;
  border:1px solid #2a2a2a;
  margin-bottom:0.6rem;
}
.card-title{
  font-size:0.72rem;font-weight:600;color:#aaa;text-transform:uppercase;
  letter-spacing:0.05em;margin-bottom:0.6rem;
  display:flex;align-items:center;gap:0.4rem;
}

/* ── Stats Grid ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:0.6rem}
.stat-row{
  display:flex;justify-content:space-between;align-items:center;
  padding:0.35rem 0;font-size:0.72rem;
  border-bottom:1px solid rgba(255,255,255,0.05)
}
.stat-row:last-child{border-bottom:none}
.stat-label{color:#888}
.stat-value{color:#ddd;font-weight:500;text-align:right}

/* ── Progress Bar ── */
.bar-wrap{height:3px;background:#2a2a2a;border-radius:2px;margin:0.2rem 0 0.35rem;overflow:hidden}
.bar-fill{height:100%;border-radius:2px;transition:width 0.5s ease}
.bar-fill.green{background:#34d399}
.bar-fill.yellow{background:#fbbf24}
.bar-fill.red{background:#fb7185}

/* ── Container List ── */
.ct-list{font-size:0.65rem;color:#777;margin-top:0.3rem;max-height:140px;overflow-y:auto}
.ct-list::-webkit-scrollbar{width:3px}
.ct-list::-webkit-scrollbar-thumb{background:#333;border-radius:2px}
.ct-list-item{
  padding:0.18rem 0;border-bottom:1px solid rgba(255,255,255,0.03);
  display:flex;gap:0.3rem;
}
.ct-id{color:#555;min-width:2rem}
.ct-name{color:#aaa}
.ct-status{color:#34d399}
.ct-status.off{color:#fb7185}

/* ── Error ── */
.error-msg{color:#fb7185;font-size:0.68rem;font-style:italic;margin-bottom:0.3rem}

/* ── Datastore ── */
.ds-row{display:flex;justify-content:space-between;font-size:0.68rem;padding:0.2rem 0;border-bottom:1px solid rgba(255,255,255,0.03)}
.ds-name{color:#a78bfa}
.ds-bar{height:2px;background:#2a2a2a;border-radius:2px;margin:0.15rem 0;overflow:hidden}

/* ── Services Grid ── */
.services-grid{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(130px,1fr));
  gap:0.5rem;
}
.service-card{
  background:#121212;
  border:1px solid #2a2a2a;
  border-radius:12px;
  padding:0.7rem 0.5rem;
  text-align:center;
  text-decoration:none;color:#fff;
  transition:border-color 0.2s;
}
.service-card:hover{border-color:#a78bfa;background:rgba(167,139,250,0.05)}
.service-card:active{transform:scale(0.97)}
.service-icon{font-size:1.4rem;margin-bottom:0.2rem}
.service-name{font-size:0.68rem;font-weight:600}
.service-cat{font-size:0.6rem;color:#888;margin-top:0.1rem}

/* ── Category Colors ── */
.cat-media{color:#22d3ee}
.cat-arr{color:#fbbf24}
.cat-download{color:#fb7185}
.cat-infra{color:#a78bfa}
.cat-monitor{color:#34d399}
.cat-security{color:#fb7185}
.cat-network{color:#fb923c}
.cat-dev{color:#94a3b8}
.cat-tools{color:#67e8f9}
.cat-docs{color:#94a3b8}
.cat-request{color:#34d399}
.cat-ai{color:#c084fc}

/* ── Architecture ── */
.arch-wrap{
  background:#121212;
  border-radius:14px;
  border:1px solid #2a2a2a;
  padding:0.8rem;
  overflow-x:auto;
}
.arch-frame{width:100%;border:none;display:block}

/* ── Footer ── */
.footer{
  text-align:center;padding:1rem 0 0.5rem;
  color:rgba(0,0,0,0.5);font-size:0.65rem;
  border-top:1px solid rgba(0,0,0,0.1);margin-top:0.5rem;
}
</style>
</head>
<body>

<div class="container">

<!-- Header -->
<div class="header">
  <div class="header-row">
    <div class="header-left">
      <span class="header-icon">🏠</span>
      <div>
        <h1>Piper Homelab</h1>
        <div class="subtitle">Anthony Piper · Las Vegas · 10.2.7.x/24</div>
      </div>
    </div>
    <div class="header-right">
      <div style="font-size:0.65rem;color:#888"><span class="status-dot"></span>All systems</div>
      <div class="last-update">{{ updated }}</div>
    </div>
  </div>
</div>

<!-- Tab Buttons -->
<div class="tab-bar">
  <button class="tab-btn active" onclick="switchTab(0)">📊 Overview</button>
  <button class="tab-btn" onclick="switchTab(1)">🔗 Services</button>
  <button class="tab-btn" onclick="switchTab(2)">🏗️ Architecture</button>
</div>

<!-- TAB: Overview -->
<div class="tab-content active" id="tab0">
  <div class="stats-grid">

    <!-- PVE1 Card -->
    <div class="card">
      <div class="card-title">🖥 PVE1 — 10.2.7.x</div>
      {% if p1.error %}<div class="error-msg">⚠ {{ p1.error[:100] }}</div>{% endif %}
      {% if p1.cpu %}<div class="stat-row"><span class="stat-label">CPU</span><span class="stat-value">{{ p1.cpu[:50] }}</span></div>{% endif %}
      <div class="stat-row"><span class="stat-label">Cores</span><span class="stat-value">{{ p1.cores or '—' }}</span></div>
      <div class="stat-row"><span class="stat-label">Load</span><span class="stat-value">{{ p1.load or '—' }}</span></div>
      <div class="stat-row"><span class="stat-label">Memory</span><span class="stat-value">{{ p1.mem_used or '?' }} / {{ p1.mem_total or '?' }}</span></div>
      {% if p1.mem_total %}
      {% set mu = p1.mem_used|replace('Gi','')|replace('Mi','')|float %}
      {% set mt = p1.mem_total|replace('Gi','')|replace('Mi','')|float %}
      {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}
      <div class="bar-wrap"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>
      {% endif %}{% endif %}
      <div class="stat-row"><span class="stat-label">Disk</span><span class="stat-value">{{ p1.disk_used or '?' }} / {{ p1.disk_total or '?' }} ({{ p1.disk_pct or '?' }})</span></div>
      {% if p1.disk_pct %}<div class="bar-wrap"><div class="bar-fill {{ p1.disk_bar or 'green' }}" style="width:{{ p1.disk_pct|replace('%','') }}%"></div></div>{% endif %}
      <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ p1.uptime or '—' }}</span></div>
      {% if p1.cts %}
      <div class="ct-list">
        <div style="color:#555;font-size:0.6rem;margin-bottom:0.2rem">CONTAINERS ({{ p1.cts|length }})</div>
        {% for ct in p1.cts %}
        {% set parts = ct.split(' | ') %}
        <div class="ct-list-item">
          <span class="ct-id">{{ parts[0] if parts|length > 0 else '' }}</span>
          <span class="ct-name">{{ parts[1] if parts|length > 1 else ct }}</span>
          <span class="ct-status {{ 'off' if parts[2]|trim|lower != 'running' else '' }}" style="margin-left:auto">{{ parts[2] if parts|length > 2 else '' }}</span>
        </div>
        {% endfor %}
      </div>
      {% endif %}
    </div>

    <!-- PVE2 Card -->
    <div class="card">
      <div class="card-title">🖥 PVE2 — 10.2.7.x</div>
      {% if p2.error %}<div class="error-msg">⚠ {{ p2.error[:100] }}</div>{% endif %}
      {% if p2.cpu %}<div class="stat-row"><span class="stat-label">CPU</span><span class="stat-value">{{ p2.cpu[:50] }}</span></div>{% endif %}
      <div class="stat-row"><span class="stat-label">Cores</span><span class="stat-value">{{ p2.cores or '—' }}</span></div>
      <div class="stat-row"><span class="stat-label">Load</span><span class="stat-value">{{ p2.load or '—' }}</span></div>
      <div class="stat-row"><span class="stat-label">Memory</span><span class="stat-value">{{ p2.mem_used or '?' }} / {{ p2.mem_total or '?' }}</span></div>
      {% if p2.mem_total %}
      {% set mu = p2.mem_used|replace('Gi','')|replace('Mi','')|float %}
      {% set mt = p2.mem_total|replace('Gi','')|replace('Mi','')|float %}
      {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}
      <div class="bar-wrap"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>
      {% endif %}{% endif %}
      <div class="stat-row"><span class="stat-label">Disk</span><span class="stat-value">{{ p2.disk_used or '?' }} / {{ p2.disk_total or '?' }} ({{ p2.disk_pct or '?' }})</span></div>
      {% if p2.disk_pct %}<div class="bar-wrap"><div class="bar-fill {{ p2.disk_bar or 'green' }}" style="width:{{ p2.disk_pct|replace('%','') }}%"></div></div>{% endif %}
      <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ p2.uptime or '—' }}</span></div>
      {% if p2.cts %}
      <div class="ct-list">
        <div style="color:#555;font-size:0.6rem;margin-bottom:0.2rem">CONTAINERS ({{ p2.cts|length }})</div>
        {% for ct in p2.cts %}
        {% set parts = ct.split(' | ') %}
        <div class="ct-list-item">
          <span class="ct-id">{{ parts[0] if parts|length > 0 else '' }}</span>
          <span class="ct-name">{{ parts[1] if parts|length > 1 else ct }}</span>
          <span class="ct-status {{ 'off' if parts[2]|trim|lower != 'running' else '' }}" style="margin-left:auto">{{ parts[2] if parts|length > 2 else '' }}</span>
        </div>
        {% endfor %}
      </div>
      {% endif %}
    </div>

    <!-- PBS Card -->
    <div class="card">
      <div class="card-title">💾 PBS — 10.2.7.x</div>
      {% if pbs.error %}<div class="error-msg">⚠ {{ pbs.error[:100] }}</div>{% endif %}
      {% if pbs.cpu %}<div class="stat-row"><span class="stat-label">CPU</span><span class="stat-value">{{ pbs.cpu[:50] }}</span></div>{% endif %}
      <div class="stat-row"><span class="stat-label">Cores</span><span class="stat-value">{{ pbs.cores or '—' }}</span></div>
      <div class="stat-row"><span class="stat-label">Version</span><span class="stat-value">{{ pbs.version or '—' }}</span></div>
      <div class="stat-row"><span class="stat-label">Load</span><span class="stat-value">{{ pbs.load or '—' }}</span></div>
      <div class="stat-row"><span class="stat-label">Memory</span><span class="stat-value">{{ pbs.mem_used or '?' }} / {{ pbs.mem_total or '?' }}</span></div>
      {% if pbs.mem_total %}
      {% set mu = pbs.mem_used|replace('Gi','')|replace('Mi','')|float %}
      {% set mt = pbs.mem_total|replace('Gi','')|replace('Mi','')|float %}
      {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}
      <div class="bar-wrap"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>
      {% endif %}{% endif %}
      <div class="stat-row"><span class="stat-label">Boot</span><span class="stat-value">{{ pbs.boot_used or '?' }} / {{ pbs.boot_total or '?' }} ({{ pbs.boot_pct or '?' }})</span></div>
      <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ pbs.uptime or '—' }}</span></div>
      {% if pbs.datastores %}
      <div style="margin-top:0.4rem;font-size:0.65rem;color:#555;margin-bottom:0.2rem">DATASTORES</div>
      {% for ds in pbs.datastores %}
      <div class="ds-row">
        <span class="ds-name">{{ ds.name }}</span>
        <span style="color:#ddd">{{ ds.used }} / {{ ds.total }} ({{ ds.pct }})</span>
      </div>
      <div class="ds-bar"><div class="bar-fill {{ ds.bar }}" style="width:{{ ds.pct|replace('%','') }}%"></div></div>
      {% endfor %}
      {% endif %}
    </div>

  </div>
</div>

<!-- TAB: Services -->
<div class="tab-content" id="tab1">
  <div class="card" style="padding:0.5rem 0.75rem 0.1rem">
    <div class="card-title" style="margin-bottom:0.3rem">🔗 All Services ({{ services|length }})</div>
  </div>
  <div class="services-grid">
  {% for s in services %}
  <a class="service-card" href="{{ s.url }}" target="_blank">
    <div class="service-icon">{{ s.icon }}</div>
    <div class="service-name">{{ s.name }}</div>
    <div class="service-cat cat-{{ s.cat }}">{{ s.cat }}</div>
  </a>
  {% endfor %}
  </div>
</div>

<!-- TAB: Architecture -->
<div class="tab-content" id="tab2">
  <div class="arch-wrap">
    <img src="/arch" alt="Homelab Architecture" class="arch-frame" />
  </div>
</div>

<div class="footer">🤖 Powered by Hermes Agent · v3 · Updated Jul 2026</div>
</div>

<script>
function switchTab(idx){
  var tabs = document.querySelectorAll('.tab-btn');
  var contents = document.querySelectorAll('.tab-content');
  tabs.forEach(function(t){ t.classList.remove('active'); });
  contents.forEach(function(c){ c.classList.remove('active'); });
  tabs[idx].classList.add('active');
  contents[idx].classList.add('active');
}
setTimeout(function(){ location.reload(); }, 60000);
</script>
</body></html>"""

@app.route("/")
def index():
    global stats_cache
    now = time.time()
    if not stats_cache["data"] or now - stats_cache["time"] > CACHE_TTL:
        stats = collect_stats()
        stats_cache["data"] = stats
        stats_cache["time"] = now
    s = stats_cache["data"]
    return render_template_string(HTML,
        updated=time.strftime("%Y-%m-%d %H:%M:%S"),
        p1=s["pve1"], p2=s["pve2"], pbs=s["pbs"],
        services=SERVICES)

@app.route("/arch")
def arch():
    return ARCH_SVG, 200, {"Content-Type": "image/svg+xml"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5052, debug=False)
