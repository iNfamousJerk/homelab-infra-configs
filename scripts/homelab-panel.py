#!/usr/bin/env python3
"""Piper Homelab — Control Panel using Proxmox REST API for live stats"""
import re, os, time, json, urllib.request, ssl
from flask import Flask, render_template_string

app = Flask(__name__)

stats_cache = {"data": None, "time": 0}
CACHE_TTL = 60

SERVICES = [
    {"name": "Jellyfin", "url": "http://10.2.7.109:8096", "icon": "🎬", "cat": "media"},
    {"name": "Radarr", "url": "http://10.2.7.109:7878", "icon": "🎥", "cat": "arr"},
    {"name": "Sonarr", "url": "http://10.2.7.109:8989", "icon": "📺", "cat": "arr"},
    {"name": "Lidarr", "url": "http://10.2.7.109:8686", "icon": "🎵", "cat": "arr"},
    {"name": "Readarr", "url": "http://10.2.7.109:8787", "icon": "📖", "cat": "arr"},
    {"name": "Prowlarr", "url": "http://10.2.7.109:9696", "icon": "🔍", "cat": "arr"},
    {"name": "Bazarr", "url": "http://10.2.7.109:6767", "icon": "💬", "cat": "arr"},
    {"name": "qBittorrent", "url": "http://10.2.7.109:8080", "icon": "⚡", "cat": "download"},
    {"name": "Navidrome", "url": "http://10.2.7.109:4533", "icon": "🎶", "cat": "media"},
    {"name": "Audiobookshelf", "url": "http://10.2.7.109:13378", "icon": "🎧", "cat": "media"},
    {"name": "Requestrr", "url": "http://10.2.7.109:4545", "icon": "📝", "cat": "request"},
    {"name": "NPM", "url": "http://10.2.7.109:81", "icon": "🔒", "cat": "infra"},
    {"name": "Grafana", "url": "http://10.2.7.108:3000", "icon": "📊", "cat": "monitor"},
    {"name": "Wazuh", "url": "https://10.2.7.110:443", "icon": "🛡️", "cat": "security"},
    {"name": "Pi-hole", "url": "http://10.2.7.2/admin", "icon": "🚫", "cat": "network"},
    {"name": "Gitea", "url": "http://10.2.7.108:3002", "icon": "🔧", "cat": "dev"},
    {"name": "Portainer", "url": "https://10.2.7.111:9443", "icon": "🐳", "cat": "infra"},
    {"name": "DVD Ripper", "url": "http://10.2.7.245:5050", "icon": "💿", "cat": "tools"},
    {"name": "Media Dash", "url": "http://10.2.7.245:5051", "icon": "📋", "cat": "tools"},
    {"name": "Homelab Panel", "url": "http://10.2.7.245:5052", "icon": "🏗️", "cat": "docs"},
]

PVE_PASSWORDS = {    "10.2.7.64": "REDACTED",
    "10.2.7.62": "REDACTED",
    "10.2.7.65": "REDACTED",
}

def pve_api(host, endpoint, password):
    """Authenticate to Proxmox API and fetch endpoint data."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    base = f"https://{host}:8006/api2/json"
    
    try:
        # Authenticate
        auth_data = urllib.parse.urlencode({"username": "root@pam", "password": password}).encode()
        req = urllib.request.Request(f"{base}/access/ticket", data=auth_data, method="POST")
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        ticket_data = json.loads(resp.read())
        ticket = ticket_data["data"]["ticket"]
        csrf = ticket_data["data"]["CSRFPreventionToken"]
        
        # Use ticket cookie
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
    
    # Get node status
    status_data = pve_api(host, "/nodes/localhost/status", password)
    if isinstance(status_data, dict) and "error" in status_data:
        s["error"] = status_data["error"]
        return s
    
    if isinstance(status_data, dict):
        s["uptime"] = f"{status_data.get('uptime', 0) / 86400:.0f}d {(status_data.get('uptime', 0) % 86400) / 3600:.0f}h" if status_data.get("uptime") else "—"
        s["load"] = " ".join(str(x) for x in status_data.get("loadavg", [])) if status_data.get("loadavg") else "—"
        # Memory
        mem_total = status_data.get("memory", {}).get("total", 0)
        mem_used = status_data.get("memory", {}).get("used", 0)
        if mem_total:
            s["mem_total"] = f"{mem_total / 1073741824:.1f}Gi" if mem_total > 1e9 else f"{mem_total / 1048576:.0f}Mi"
            s["mem_used"] = f"{mem_used / 1073741824:.1f}Gi" if mem_used > 1e9 else f"{mem_used / 1048576:.0f}Mi"
        # Root disk (rootfs is a flat dict in Proxmox API)
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
        # CPU info from status (already available)
        if isinstance(status_data.get("cpuinfo"), dict):
            ci = status_data["cpuinfo"]
            if not s.get("cpu"): s["cpu"] = ci.get("model", "—").strip()
            if not s.get("cores"): s["cores"] = ci.get("cpus", "—")
        # Also try the hardware endpoint for full CPU model
        cpuinfo = pve_api(host, "/nodes/localhost/hardware/cpu", password)
        if isinstance(cpuinfo, list) and len(cpuinfo) > 0:
            s["cpu"] = cpuinfo[0].get("model", "").strip()
        # Get containers using local node endpoints (more reliable per-node)
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
        
        # Version
        version_data = pbs_get("/version")
        if isinstance(version_data, dict):
            s["version"] = version_data.get("version", "—")
        
        # Get node status for system stats (memory, load, uptime, CPU)
        try:
            ns = pbs_get("/nodes/localhost/status")
            if isinstance(ns, dict):
                # CPU info
                if isinstance(ns.get("cpuinfo"), dict):
                    s["cpu"] = ns["cpuinfo"].get("model", "—")
                    s["cores"] = ns["cpuinfo"].get("cpus", "—")
                # Memory
                mem = ns.get("memory", {})
                if mem.get("total"):
                    s["mem_total"] = f"{mem['total'] / 1073741824:.1f}Gi"
                    s["mem_used"] = f"{mem['used'] / 1073741824:.1f}Gi"
                # Load
                if ns.get("loadavg"):
                    s["load"] = " ".join(str(x) for x in ns["loadavg"])
                # Uptime
                if ns.get("uptime"):
                    upt = ns["uptime"]
                    s["uptime"] = f"{upt // 86400:.0f}d {(upt % 86400) // 3600:.0f}h"
                # Root disk (boot drive)
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
        
        # Get ALL datastores
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
        # Set primary disk to first datastore for the overview
        if s.get("datastores"):
            s["disk_total"] = s["datastores"][0]["total"]
            s["disk_used"] = s["datastores"][0]["used"]
            s["disk_pct"] = s["datastores"][0]["pct"]
        
    except Exception as e:
        s["error"] = str(e)
    return s

def collect_stats():
    pve1 = parse_node_status("10.2.7.64", "PVE1", PVE_PASSWORDS.get("10.2.7.64", ""))
    pve2 = parse_node_status("10.2.7.62", "PVE2", PVE_PASSWORDS.get("10.2.7.62", ""))
    pbs = parse_pbs_status("10.2.7.65", "PBS", PVE_PASSWORDS.get("10.2.7.65", ""))
    return {"pve1": pve1, "pve2": pve2, "pbs": pbs}

# ─── Architecture SVG ───────────────────────────────────────────
ARCH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 850" style="background:#020617;width:100%;height:auto;max-width:1100px">
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
.line{stroke:#334155;stroke-width:1.5;fill:none}
.line-glow{stroke:#22d3ee;stroke-width:1;fill:none;opacity:0.3}
.title{font-size:13px;font-weight:bold;fill:#f1f5f9}
.sub{font-size:10px;fill:#64748b}
.highlight{fill:#a78bfa;font-weight:bold}
</style>
<!-- Title -->
<text x="550" y="30" text-anchor="middle" class="title">🏠 Piper Homelab Topology</text>
<text x="550" y="46" text-anchor="middle" class="sub">Las Vegas · 10.2.7.0/24 · Proxmox Cluster</text>
<!-- === INTERNET === -->
<rect x="450" y="60" width="200" height="36" class="box"/>
<text x="550" y="77" text-anchor="middle" font-size="12" fill="#34d399">🌐 Internet</text>
<text x="550" y="90" text-anchor="middle" class="label">Comcast Cable</text>
<line x1="550" y1="96" x2="550" y2="118" class="line"/>
<!-- === OPNsense === -->
<rect x="400" y="120" width="300" height="44" class="box" stroke="#fb923c"/>
<text x="550" y="140" text-anchor="middle" font-size="12" class="net">🛡 OPNsense</text>
<text x="550" y="155" text-anchor="middle" class="label">VLANs: Family (10.2.10.1) · Server (10.2.30.1) · Guest (10.2.20.1) · LAN (10.2.7.1)</text>
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
<text x="220" y="269" text-anchor="middle" font-size="12" class="hl">🖥 PVE1 — 10.2.7.64</text>
<text x="220" y="282" text-anchor="middle" class="label">i5-7500 · 31GB RAM · 94GB SSD</text>
<rect x="95" y="295" width="250" height="245" class="box2"/>
<text x="220" y="312" text-anchor="middle" class="label" font-size="9">CONTAINERS</text>
<rect x="105" y="320" width="110" height="34" class="box3"/><text x="160" y="335" text-anchor="middle" font-size="10" class="infra">🤖 Hermes (100)</text><text x="160" y="348" text-anchor="middle" class="label">AI Agent</text>
<rect x="225" y="320" width="110" height="34" class="box3"/><text x="280" y="335" text-anchor="middle" font-size="10" class="sec">⚠ PiAlert (102)</text><text x="280" y="348" text-anchor="middle" class="label">Network Alerts</text>
<rect x="105" y="360" width="110" height="34" class="box3"/><text x="160" y="375" text-anchor="middle" font-size="10" class="sec">🛡 Wazuh (105)</text><text x="160" y="388" text-anchor="middle" class="label">SIEM · 10.2.7.110</text>
<rect x="225" y="360" width="110" height="34" class="box3"/><text x="280" y="375" text-anchor="middle" font-size="10" class="mon">📊 Grafana (106)</text><text x="280" y="388" text-anchor="middle" class="label">Monitoring</text>
<rect x="105" y="400" width="110" height="34" class="box3"/><text x="160" y="415" text-anchor="middle" font-size="10" class="net">🚫 Pi-hole (107)</text><text x="160" y="428" text-anchor="middle" class="label">DNS · 10.2.7.2</text>
<rect x="225" y="400" width="110" height="34" class="box3"/><text x="280" y="415" text-anchor="middle" font-size="10" class="infra">🐳 Portainer (108)</text><text x="280" y="428" text-anchor="middle" class="label">Docker Manager</text>
<rect x="105" y="440" width="110" height="34" class="box3"/><text x="160" y="455" text-anchor="middle" font-size="10" class="infra">📋 Dashboards (109)</text><text x="160" y="468" text-anchor="middle" class="label">Heimdall</text>
<rect x="225" y="440" width="110" height="34" class="box3"/><text x="280" y="455" text-anchor="middle" font-size="10" class="infra">🤖 Hermes Ollama (113)</text><text x="280" y="468" text-anchor="middle" class="label">Local LLM</text>
<text x="220" y="530" text-anchor="middle" class="label">🔗 VLAN: Server (10.2.30.1)</text>
<!-- === PVE2 === -->
<rect x="450" y="252" width="200" height="36" class="box" stroke="#22d3ee"/>
<text x="550" y="269" text-anchor="middle" font-size="12" class="hl">🖥 PVE2 — 10.2.7.62</text>
<text x="550" y="282" text-anchor="middle" class="label">i7-2600 · 16GB RAM · 2.72TB ZFS</text>
<rect x="425" y="295" width="250" height="195" class="box2"/>
<text x="550" y="312" text-anchor="middle" class="label" font-size="9">CONTAINERS</text>
<rect x="435" y="320" width="110" height="34" class="box3"/><text x="490" y="335" text-anchor="middle" font-size="10" class="sec">🔍 Zeek (101)</text><text x="490" y="348" text-anchor="middle" class="label">IDS Sensor</text>
<rect x="555" y="320" width="110" height="34" class="box3"/><text x="610" y="335" text-anchor="middle" font-size="10" class="tools">💿 Ripper (103)</text><text x="610" y="348" text-anchor="middle" class="label">DVD Ripping</text>
<rect x="435" y="360" width="150" height="34" class="box3"/><text x="510" y="375" text-anchor="middle" font-size="10" class="media">🎬 Media Stack (110)</text><text x="510" y="388" text-anchor="middle" class="label">Jellyfin + *arrs</text>
<rect x="435" y="400" width="110" height="34" class="box3"/><text x="490" y="415" text-anchor="middle" font-size="10" class="media">📸 Immich (111)</text><text x="490" y="428" text-anchor="middle" class="label">Photo Backup</text>
<rect x="555" y="400" width="110" height="34" class="box3"/><text x="610" y="415" text-anchor="middle" font-size="10" class="infra">☁ Nextcloud (112)</text><text x="610" y="428" text-anchor="middle" class="label">File Sync</text>
<text x="550" y="480" text-anchor="middle" class="label">🔗 VLAN: Server (10.2.30.1) · ZFS: media pool</text>
<!-- === PBS === -->
<rect x="780" y="252" width="200" height="36" class="box" stroke="#a78bfa"/>
<text x="880" y="269" text-anchor="middle" font-size="12" class="infra">💾 PBS — 10.2.7.65</text>
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
<rect x="200" y="560" width="700" height="56" class="box" stroke="#fbbf24"/>
<text x="550" y="580" text-anchor="middle" font-size="12" class="arr">📺 Media Stack — CT 110 (10.2.7.109)</text>
<text x="550" y="598" text-anchor="middle" class="label">🎬 Jellyfin :8096 · 🎥 Radarr :7878 · 📺 Sonarr :8989 · 🔍 Prowlarr :9696 · ⚡ qBit :8080 · 🎶 Navidrome :4533 · 📝 Requestrr :4545</text>
<rect x="200" y="637" width="700" height="44" class="box" stroke="#34d399"/>
<text x="550" y="657" text-anchor="middle" font-size="12" class="mon">💾 Storage Layout</text>
<text x="550" y="673" text-anchor="middle" class="label">PVE1: 94GB SSD (boot) · PVE2: 2TB+1TB ZFS mirror (@ /media/data, ~746GB used) · PBS: 3TB Hitachi @ media-backups</text>
<rect x="200" y="690" width="700" height="30" class="box" stroke="#fb923c"/>
<text x="550" y="710" text-anchor="middle" class="label" font-size="11">📁 SMB: \\\\10.2.7.109\\Media · \\\\10.2.7.44\\Immich · \\\\10.2.7.99\\Nextcloud — user: media/media</text>
<rect x="200" y="735" width="700" height="50" class="box2"/>
<text x="230" y="752" class="label" font-size="9">Legend:</text>
<rect x="290" y="743" width="10" height="10" rx="2" fill="#22d3ee"/><text x="305" y="752" font-size="9" fill="#22d3ee">Proxmox</text>
<rect x="380" y="743" width="10" height="10" rx="2" fill="#fbbf24"/><text x="395" y="752" font-size="9" fill="#fbbf24">Media</text>
<rect x="455" y="743" width="10" height="10" rx="2" fill="#34d399"/><text x="470" y="752" font-size="9" fill="#34d399">Infra</text>
<rect x="530" y="743" width="10" height="10" rx="2" fill="#fb7185"/><text x="545" y="752" font-size="9" fill="#fb7185">Security</text>
<rect x="620" y="743" width="10" height="10" rx="2" fill="#fb923c"/><text x="635" y="752" font-size="9" fill="#fb923c">Network</text>
<rect x="710" y="743" width="10" height="10" rx="2" fill="#a78bfa"/><text x="725" y="752" font-size="9" fill="#a78bfa">PBS/Backup</text>
<text x="550" y="778" text-anchor="middle" class="sub" font-size="9">Generated by Hermes Agent · Stats update every 60s</text>
</svg>"""

# ─── HTML Template ─────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Piper Homelab</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#020617;color:white;padding:1.5rem}
.container{max-width:1200px;margin:0 auto}
h1{font-size:1.5rem;font-weight:700;margin-bottom:0.25rem}
.subtitle{color:#64748b;font-size:0.8rem;margin-bottom:0.25rem}
.last-update{color:#475569;font-size:0.7rem;margin-bottom:1.5rem}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1rem;margin-bottom:1.5rem}
.host-card{background:rgba(15,23,42,0.5);border:1px solid #1e293b;border-radius:0.75rem;padding:1.25rem}
.host-card h2{font-size:1rem;margin-bottom:0.75rem;display:flex;align-items:center;gap:0.5rem}
.host-card .dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.dot.green{background:#34d399}
.dot.yellow{background:#fbbf24}
.dot.red{background:#fb7185}
.stat-row{display:flex;justify-content:space-between;padding:0.3rem 0;font-size:0.75rem;border-bottom:1px solid rgba(30,41,59,0.5)}
.stat-row:last-child{border-bottom:none}
.stat-label{color:#64748b}
.stat-value{color:#e2e8f0}
.ct-list{margin-top:0.5rem;font-size:0.65rem;color:#94a3b8;max-height:160px;overflow-y:auto}
.ct-list div{padding:0.15rem 0;border-bottom:1px solid rgba(30,41,59,0.3)}
.ct-list div:last-child{border:none}
.services-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:0.75rem;margin-bottom:1.5rem}
.service-card{background:rgba(15,23,42,0.5);border:1px solid #1e293b;border-radius:0.5rem;padding:0.75rem;text-align:center;text-decoration:none;color:white;transition:border-color 0.2s}
.service-card:hover{border-color:#22d3ee;background:rgba(34,211,238,0.05)}
.service-icon{font-size:1.5rem;margin-bottom:0.25rem}
.service-name{font-size:0.7rem;font-weight:600}
.service-cat{font-size:0.6rem;color:#64748b;margin-top:0.15rem}
.arr{color:#fbbf24}.media{color:#22d3ee}.monitor{color:#34d399}.security{color:#fb7185}.infra{color:#a78bfa}.network{color:#fb923c}.dev{color:#e2e8f0}.download{color:#fb7185}.tools{color:#67e8f9}.docs{color:#94a3b8}.request{color:#34d399}
.bar{height:4px;background:#1e293b;border-radius:2px;margin-top:0.2rem;width:100%;margin-bottom:0.3rem}
.bar-fill{height:100%;border-radius:2px}.bar-fill.green{background:#34d399}.bar-fill.yellow{background:#fbbf24}.bar-fill.red{background:#fb7185}
.tabs{display:flex;gap:0.5rem;margin-bottom:1.5rem;border-bottom:1px solid #1e293b}
.tab{padding:0.5rem 1rem;cursor:pointer;font-size:0.8rem;color:#64748b;border-radius:0.5rem 0.5rem 0 0}
.tab:hover{color:#e2e8f0}
.tab.active{color:#22d3ee;background:rgba(15,23,42,0.5);border:1px solid #1e293b;border-bottom:2px solid #22d3ee}
.tab-content{display:none}
.tab-content.active{display:block}
.arch-frame{width:100%;border:none;border-radius:0.5rem;background:transparent}
.footer{margin-top:2rem;color:#475569;font-size:0.7rem;text-align:center;border-top:1px solid #1e293b;padding-top:1rem}
.error-msg{color:#fb7185;font-size:0.7rem;font-style:italic}
</style>
</head>
<body>
<div class="container">
<h1>🏠 Piper Homelab</h1>
<p class="subtitle">Anthony Piper · Las Vegas · 10.2.7.0/24</p>
<p class="last-update">Last updated: {{ updated }} · Auto-refreshes every 60s</p>

<div class="tabs">
<div class="tab active" onclick="switchTab('overview')">📊 Overview</div>
<div class="tab" onclick="switchTab('services')">🔗 Services</div>
<div class="tab" onclick="switchTab('architecture')">🏗️ Architecture</div>
</div>

<!-- Overview Tab -->
<div id="tab-overview" class="tab-content active">
<div class="stats-grid">
  <!-- PVE1 -->
  <div class="host-card">
    <h2><span class="dot {{ 'green' if p1.uptime else 'red' }}"></span> PVE1 — 10.2.7.64</h2>
    {% if p1.error %}<div class="error-msg">⚠ {{ p1.error[:100] }}</div>{% endif %}
    {% if p1.cpu %}<div class="stat-row"><span class="stat-label">CPU</span><span class="stat-value">{{ p1.cpu[:50] }}</span></div>{% endif %}
    <div class="stat-row"><span class="stat-label">Cores</span><span class="stat-value">{{ p1.cores or '—' }}</span></div>
    <div class="stat-row"><span class="stat-label">Load</span><span class="stat-value">{{ p1.load or '—' }}</span></div>
    <div class="stat-row"><span class="stat-label">Memory</span><span class="stat-value">{{ p1.mem_used or '?' }} / {{ p1.mem_total or '?' }}</span></div>
    {% if p1.mem_total %}
    {% set mu = p1.mem_used|replace('Gi','')|replace('Mi','')|float %}
    {% set mt = p1.mem_total|replace('Gi','')|replace('Mi','')|float %}
    {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}<div class="bar"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>{% endif %}
    {% endif %}
    <div class="stat-row"><span class="stat-label">Disk</span><span class="stat-value">{{ p1.disk_used or '?' }} / {{ p1.disk_total or '?' }} ({{ p1.disk_pct or '?' }})</span></div>
    <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ p1.uptime or '—' }}</span></div>
    {% if p1.cts %}
    <div class="ct-list">
      <div style="color:#64748b;font-size:0.65rem;margin-bottom:0.25rem">CONTAINERS</div>
      {% for ct in p1.cts %}
      <div>⬢ {{ ct }}</div>
      {% endfor %}
    </div>
    {% endif %}
  </div>

  <!-- PVE2 -->
  <div class="host-card">
    <h2><span class="dot {{ 'green' if p2.uptime else 'red' }}"></span> PVE2 — 10.2.7.62</h2>
    {% if p2.error %}<div class="error-msg">⚠ {{ p2.error[:100] }}</div>{% endif %}
    {% if p2.cpu %}<div class="stat-row"><span class="stat-label">CPU</span><span class="stat-value">{{ p2.cpu[:50] }}</span></div>{% endif %}
    <div class="stat-row"><span class="stat-label">Cores</span><span class="stat-value">{{ p2.cores or '—' }}</span></div>
    <div class="stat-row"><span class="stat-label">Load</span><span class="stat-value">{{ p2.load or '—' }}</span></div>
    <div class="stat-row"><span class="stat-label">Memory</span><span class="stat-value">{{ p2.mem_used or '?' }} / {{ p2.mem_total or '?' }}</span></div>
    {% if p2.mem_total %}
    {% set mu = p2.mem_used|replace('Gi','')|replace('Mi','')|float %}
    {% set mt = p2.mem_total|replace('Gi','')|replace('Mi','')|float %}
    {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}<div class="bar"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>{% endif %}
    {% endif %}
    <div class="stat-row"><span class="stat-label">Disk</span><span class="stat-value">{{ p2.disk_used or '?' }} / {{ p2.disk_total or '?' }} ({{ p2.disk_pct or '?' }})</span></div>
    <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ p2.uptime or '—' }}</span></div>
    {% if p2.cts %}
    <div class="ct-list">
      <div style="color:#64748b;font-size:0.65rem;margin-bottom:0.25rem">CONTAINERS</div>
      {% for ct in p2.cts %}
      <div>⬢ {{ ct }}</div>
      {% endfor %}
    </div>
    {% endif %}
  </div>

  <!-- PBS -->
  <div class="host-card">
    <h2><span class="dot {{ 'green' if pbs.uptime else 'red' }}"></span> PBS — 10.2.7.65</h2>
    {% if pbs.error %}<div class="error-msg">⚠ {{ pbs.error[:100] }}</div>{% endif %}
    {% if pbs.cpu %}<div class="stat-row"><span class="stat-label">CPU</span><span class="stat-value">{{ pbs.cpu[:50] }}</span></div>{% endif %}
    <div class="stat-row"><span class="stat-label">Cores</span><span class="stat-value">{{ pbs.cores or '—' }}</span></div>
    <div class="stat-row"><span class="stat-label">Version</span><span class="stat-value">{{ pbs.version or '—' }}</span></div>
    <div class="stat-row"><span class="stat-label">Load</span><span class="stat-value">{{ pbs.load or '—' }}</span></div>
    <div class="stat-row"><span class="stat-label">Memory</span><span class="stat-value">{{ pbs.mem_used or '?' }} / {{ pbs.mem_total or '?' }}</span></div>
    {% if pbs.mem_total %}
    {% set mu = pbs.mem_used|replace('Gi','')|replace('Mi','')|float %}
    {% set mt = pbs.mem_total|replace('Gi','')|replace('Mi','')|float %}
    {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}<div class="bar"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>{% endif %}
    {% endif %}
    <div class="stat-row"><span class="stat-label">Boot</span><span class="stat-value">{{ pbs.boot_used or '?' }} / {{ pbs.boot_total or '?' }} ({{ pbs.boot_pct or '?' }})</span></div>
    <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ pbs.uptime or '—' }}</span></div>
    {% if pbs.datastores %}
    <div style="margin-top:0.5rem;font-size:0.65rem;color:#94a3b8;margin-bottom:0.25rem">DATASTORES</div>
    {% for ds in pbs.datastores %}
    <div class="stat-row"><span class="stat-label">{{ ds.name }}</span><span class="stat-value">{{ ds.used }} / {{ ds.total }} ({{ ds.pct }})</span></div>
    {% endfor %}
    {% endif %}
  </div>
</div>
</div>

<!-- Services Tab -->
<div id="tab-services" class="tab-content">
<div class="services-grid">
{% for s in services %}
<a class="service-card" href="{{ s.url }}" target="_blank">
<div class="service-icon">{{ s.icon }}</div>
<div class="service-name">{{ s.name }}</div>
<div class="service-cat {{ s.cat }}">{{ s.cat }}</div>
</a>
{% endfor %}
</div>
</div>

<!-- Architecture Tab -->
<div id="tab-architecture" class="tab-content">
<img src="/arch" alt="Homelab Architecture" class="arch-frame" />
</div>

<p class="footer">🤖 Powered by Hermes · CT 103 (10.2.7.245)</p>
</div>

<script>
function switchTab(n){
document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
document.querySelectorAll(".tab-content").forEach(t=>t.classList.remove("active"));
var tabs=document.querySelectorAll(".tab");
var contents=document.querySelectorAll(".tab-content");
var idx={overview:0,services:1,architecture:2}[n]||0;
tabs[idx].classList.add("active");
contents[idx].classList.add("active");
}
setTimeout(function(){location.reload()},60000);
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
    app.run(host="0.0.0.0", port=5052, debug=False, threaded=True)