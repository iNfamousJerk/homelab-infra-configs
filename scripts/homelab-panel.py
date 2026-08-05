#!/usr/bin/env python3
"""Piper Homelab — Cyberpunk Control Panel v4"""
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
    {"name": "Librarr", "url": "http://10.2.7.x:5050", "icon": "📚", "cat": "arr"},
    {"name": "Prowlarr", "url": "http://10.2.7.x:9696", "icon": "🔍", "cat": "arr"},
    {"name": "Bazarr", "url": "http://10.2.7.x:6767", "icon": "💬", "cat": "arr"},
    {"name": "Jellyseerr", "url": "http://10.2.7.x:5055", "icon": "📺", "cat": "request"},
    {"name": "Mylar3", "url": "http://10.2.7.x:8090", "icon": "📚", "cat": "arr"},
    {"name": "Manga Request", "url": "http://10.2.7.x:5000", "icon": "🎴", "cat": "request"},
    {"name": "qBittorrent", "url": "http://10.2.7.x:8080", "icon": "⚡", "cat": "download"},
    {"name": "Navidrome", "url": "http://10.2.7.x:4533", "icon": "🎶", "cat": "media"},
    {"name": "Audiobookshelf", "url": "http://10.2.7.x:13378", "icon": "🎧", "cat": "media"},
    {"name": "Requestrr", "url": "http://10.2.7.x:4545", "icon": "📝", "cat": "request"},
    {"name": "Immich", "url": "http://10.2.7.x:2283", "icon": "📸", "cat": "media"},
    {"name": "Nextcloud", "url": "http://10.2.7.x:80", "icon": "☁️", "cat": "infra"},
    {"name": "NPM", "url": "http://10.2.7.x:81", "icon": "🔒", "cat": "infra"},
    {"name": "Grafana", "url": "http://10.2.7.x:3000", "icon": "📊", "cat": "monitor"},
    {"name": "Prometheus", "url": "http://10.2.7.x:9090", "icon": "📈", "cat": "monitor"},
    {"name": "Uptime Kuma", "url": "http://10.2.7.x:3001", "icon": "❤️", "cat": "monitor"},
    {"name": "Wazuh", "url": "https://10.2.7.x:443", "icon": "🛡️", "cat": "security"},
    {"name": "Pi-hole", "url": "http://10.2.7.x/admin", "icon": "🚫", "cat": "network"},
    {"name": "Gitea", "url": "http://10.2.7.x:3002", "icon": "🔧", "cat": "dev"},
    {"name": "Portainer", "url": "https://10.2.7.x:9443", "icon": "🐳", "cat": "infra"},
    {"name": "Cockpit", "url": "https://10.2.7.x:9090", "icon": "🖥️", "cat": "infra"},
    {"name": "HO (Ollama)", "url": "http://10.2.7.x:11434", "icon": "🧠", "cat": "ai"},
    {"name": "Donetick", "url": "http://10.2.7.x:2021", "icon": "✅", "cat": "tools"},
    {"name": "DVD Ripper", "url": "http://10.2.7.x:5050", "icon": "💿", "cat": "tools"},
    {"name": "Media Dash", "url": "http://10.2.7.x:5051", "icon": "📋", "cat": "tools"},
    {"name": "osTicket", "url": "http://10.2.7.x:8081", "icon": "🎫", "cat": "tools"},
    {"name": "Snipe-IT", "url": "http://10.2.7.x:8000", "icon": "📦", "cat": "infra"},
    {"name": "Keycloak", "url": "http://10.2.7.x:5252", "icon": "🔑", "cat": "security"},
    {"name": "Homelab Panel", "url": "http://10.2.7.x:5052", "icon": "🏗️", "cat": "docs"},
]

PVE_PASSWORDS = {
    "10.2.7.x": "2proxtheworld",
    "10.2.7.x": "2proxtheworld",
    "10.2.7.x": "2backuptheworld",
}

def pve_api(host, endpoint, password):
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

ARCH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 870" style="background:#08080f;width:100%;height:auto;max-width:1100px">
<style>
text{font-family:'JetBrains Mono','Courier New',monospace;fill:#c0c0e0;font-size:11px}
.box{fill:rgba(10,10,25,0.85);stroke:#ff00aa;stroke-width:1.5;rx:6;ry:6;filter:url(#glow)}
.box2{fill:rgba(15,15,30,0.6);stroke:#ff00aa44;stroke-width:1;rx:4;ry:4}
.box3{fill:rgba(10,10,25,0.5);stroke:#00f0ff66;stroke-width:1;rx:4;ry:4}
.label{font-size:10px;fill:#8888aa}
.hl{fill:#00f0ff;font-weight:bold}
.arr{fill:#ffd700}
.media{fill:#00f0ff}
.mon{fill:#00ff41}
.sec{fill:#ff0044}
.infra{fill:#ff00aa}
.net{fill:#ff8800}
.ai{fill:#aa66ff}
.line{stroke:#ff00aa44;stroke-width:1.5;fill:none}
.title{font-size:13px;font-weight:bold;fill:#00f0ff}
.sub{font-size:10px;fill:#6666aa}
</style>
<defs>
<filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect width="1100" height="870" fill="#08080f"/>
<text x="550" y="30" text-anchor="middle" class="title">🏴 Piper Homelab Topology</text>
<text x="550" y="46" text-anchor="middle" class="sub">Las Vegas · 10.2.7.x/24 · Proxmox Cluster</text>
<!-- INTERNET -->
<rect x="450" y="60" width="200" height="36" class="box"/>
<text x="550" y="77" text-anchor="middle" font-size="12" fill="#00ff41">🌐 Internet</text>
<text x="550" y="90" text-anchor="middle" class="label">Comcast Cable</text>
<line x1="550" y1="96" x2="550" y2="118" class="line"/>
<!-- OPNsense -->
<rect x="400" y="120" width="300" height="44" class="box" stroke="#ff8800"/>
<text x="550" y="140" text-anchor="middle" font-size="12" class="net">🛡 OPNsense — 10.2.7.x</text>
<text x="550" y="155" text-anchor="middle" class="label">Firewall · VLANs · DHCP · NAT</text>
<line x1="550" y1="164" x2="550" y2="182" class="line"/>
<!-- Switch -->
<rect x="400" y="184" width="300" height="36" class="box" stroke="#00ff41"/>
<text x="550" y="200" text-anchor="middle" font-size="12" class="mon">🔀 TP-Link TL-SG108E</text>
<text x="550" y="214" text-anchor="middle" class="label">8-Port Gigabit Smart Switch</text>
<line x1="220" y1="220" x2="220" y2="250" class="line"/>
<line x1="550" y1="220" x2="550" y2="250" class="line"/>
<line x1="880" y1="220" x2="880" y2="250" class="line"/>
<!-- PVE1 -->
<rect x="120" y="252" width="200" height="36" class="box" stroke="#00f0ff"/>
<text x="220" y="269" text-anchor="middle" font-size="12" class="hl">🖥 PVE1 — 10.2.7.x</text>
<text x="220" y="282" text-anchor="middle" class="label">i5-7500 · 31GB RAM · 94GB SSD</text>
<rect x="95" y="295" width="250" height="330" class="box2"/>
<text x="220" y="312" text-anchor="middle" class="label" font-size="9">CONTAINERS</text>
<rect x="105" y="320" width="110" height="34" class="box3"/><text x="160" y="335" text-anchor="middle" font-size="10" class="infra">🤖 Hermes (100)</text><text x="160" y="348" text-anchor="middle" class="label">AI Agent · 10.2.7.x</text>
<rect x="225" y="320" width="110" height="34" class="box3"/><text x="280" y="335" text-anchor="middle" font-size="10" class="mon">✅ Donetick (102)</text><text x="280" y="348" text-anchor="middle" class="label">Tasks · 10.2.7.x</text>
<rect x="105" y="360" width="110" height="34" class="box3"/><text x="160" y="375" text-anchor="middle" font-size="10" class="sec">🛡 Wazuh (105)</text><text x="160" y="388" text-anchor="middle" class="label">SIEM · 10.2.7.x</text>
<rect x="225" y="360" width="110" height="34" class="box3"/><text x="280" y="375" text-anchor="middle" font-size="10" class="mon">📊 Grafana (106)</text><text x="280" y="388" text-anchor="middle" class="label">Monitoring · 10.2.7.x</text>
<rect x="105" y="400" width="110" height="34" class="box3"/><text x="160" y="415" text-anchor="middle" font-size="10" class="net">🚫 Pi-hole (107)</text><text x="160" y="428" text-anchor="middle" class="label">DNS · 10.2.7.x</text>
<rect x="225" y="400" width="110" height="34" class="box3"/><text x="280" y="415" text-anchor="middle" font-size="10" class="infra">🐳 Portainer (108)</text><text x="280" y="428" text-anchor="middle" class="label">Docker Mgr</text>
<rect x="105" y="440" width="110" height="34" class="box3"/><text x="160" y="455" text-anchor="middle" font-size="10" class="infra">📋 Heimdall (109)</text><text x="160" y="468" text-anchor="middle" class="label">Dashboard</text>
<rect x="225" y="440" width="110" height="34" class="box3"/><text x="280" y="455" text-anchor="middle" font-size="10" class="mon">❤️ Uptime Kuma</text><text x="280" y="468" text-anchor="middle" class="label">Uptime</text>
<rect x="105" y="480" width="110" height="34" class="box3"/><text x="160" y="495" text-anchor="middle" font-size="10" class="media">📸 Immich (111)</text><text x="160" y="508" text-anchor="middle" class="label">Photos</text>
<rect x="225" y="480" width="110" height="34" class="box3"/><text x="280" y="495" text-anchor="middle" font-size="10" class="ai">🧠 HO (113)</text><text x="280" y="508" text-anchor="middle" class="label">Ollama · 10.2.7.x</text>
<rect x="105" y="520" width="110" height="34" class="box3"/><text x="160" y="535" text-anchor="middle" font-size="10" class="infra">🖥️ Cockpit (114)</text><text x="160" y="548" text-anchor="middle" class="label">Web Admin</text>
<rect x="225" y="520" width="110" height="34" class="box3"/><text x="280" y="535" text-anchor="middle" font-size="10" class="infra">☁ Nextcloud (112)</text><text x="280" y="548" text-anchor="middle" class="label">File Sync · 10.2.7.x</text>
<text x="220" y="610" text-anchor="middle" class="label">🔗 10.2.7.x/24 subnet</text>
<!-- PVE2 -->
<rect x="450" y="252" width="200" height="36" class="box" stroke="#00f0ff"/>
<text x="550" y="269" text-anchor="middle" font-size="12" class="hl">🖥 PVE2 — 10.2.7.x</text>
<text x="550" y="282" text-anchor="middle" class="label">i7-2600 · 31GB RAM · 3.62TB ZFS</text>
<rect x="425" y="295" width="250" height="195" class="box2"/>
<text x="550" y="312" text-anchor="middle" class="label" font-size="9">CONTAINERS</text>
<rect x="435" y="320" width="110" height="34" class="box3"/><text x="490" y="335" text-anchor="middle" font-size="10" class="sec">🔍 Zeek (101)</text><text x="490" y="348" text-anchor="middle" class="label">IDS Sensor</text>
<rect x="555" y="320" width="110" height="34" class="box3"/><text x="610" y="335" text-anchor="middle" font-size="10" class="tools">💿 Ripper (103)</text><text x="610" y="348" text-anchor="middle" class="label">DVD Ripping</text>
<rect x="435" y="360" width="150" height="34" class="box3"/><text x="510" y="375" text-anchor="middle" font-size="10" class="media">🎬 Media Stack (110)</text><text x="510" y="388" text-anchor="middle" class="label">Jellyfin + *arrs</text>
<text x="550" y="480" text-anchor="middle" class="label">🔗 ZFS: media · 4×2TB mirror</text>
<!-- PBS -->
<rect x="780" y="252" width="200" height="36" class="box" stroke="#ff00aa"/>
<text x="880" y="269" text-anchor="middle" font-size="12" class="infra">💾 PBS — 10.2.7.x</text>
<text x="880" y="282" text-anchor="middle" class="label">Xeon E3-1225 · 15GB · 3TB</text>
<rect x="760" y="295" width="240" height="120" class="box2"/>
<text x="880" y="315" text-anchor="middle" class="label" font-size="9">BACKUP SERVER</text>
<text x="790" y="340" class="label">• Deduplicated backups</text>
<text x="790" y="358" class="label">• All CTs @ daily 03:30, 15:30</text>
<text x="790" y="376" class="label">• Media stack @ :33 past</text>
<text x="790" y="394" class="label">• Hitachi 3TB HDD</text>
<!-- Bottom -->
<rect x="200" y="560" width="700" height="44" class="box" stroke="#ffd700"/>
<text x="550" y="578" text-anchor="middle" font-size="12" class="arr">📺 Media Stack — CT 110 (10.2.7.x)</text>
<text x="550" y="594" text-anchor="middle" class="label">🎬 Jellyfin · 🎥 Radarr · 📺 Sonarr · 🔍 Prowlarr · ⚡ qBit · 🎶 Navidrome · 📝 Requestrr</text>
<rect x="200" y="620" width="700" height="44" class="box" stroke="#00ff41"/>
<text x="550" y="640" text-anchor="middle" font-size="12" class="mon">💾 Storage Layout</text>
<text x="550" y="656" text-anchor="middle" class="label">PVE1: 94GB SSD · PVE2: 4×2TB ZFS mirror (~2.63T used / 3.62T) · PBS: 3TB HDD</text>
<rect x="200" y="690" width="700" height="30" class="box" stroke="#ff8800"/>
<text x="550" y="710" text-anchor="middle" class="label" font-size="11">🔗 Tailscale mesh · ProtonVPN via Gluetun · Pi-hole DNS · Wazuh SIEM</text>
<rect x="200" y="735" width="700" height="50" class="box2"/>
<text x="230" y="752" class="label" font-size="9">Legend:</text>
<rect x="290" y="743" width="10" height="10" rx="2" fill="#00f0ff"/><text x="305" y="752" font-size="9" fill="#00f0ff">Proxmox</text>
<rect x="380" y="743" width="10" height="10" rx="2" fill="#ffd700"/><text x="395" y="752" font-size="9" fill="#ffd700">Media</text>
<rect x="455" y="743" width="10" height="10" rx="2" fill="#00ff41"/><text x="470" y="752" font-size="9" fill="#00ff41">Monitoring</text>
<rect x="530" y="743" width="10" height="10" rx="2" fill="#ff0044"/><text x="545" y="752" font-size="9" fill="#ff0044">Security</text>
<rect x="620" y="743" width="10" height="10" rx="2" fill="#ff8800"/><text x="635" y="752" font-size="9" fill="#ff8800">Network</text>
<rect x="710" y="743" width="10" height="10" rx="2" fill="#ff00aa"/><text x="725" y="752" font-size="9" fill="#ff00aa">Infra/Backup</text>
<rect x="790" y="743" width="10" height="10" rx="2" fill="#aa66ff"/><text x="805" y="752" font-size="9" fill="#aa66ff">AI</text>
<text x="550" y="778" text-anchor="middle" class="sub" font-size="9">Cyberpunk Homelab · Generated by Hermes Agent · v4 · Updated Aug 4 2026</text>
</svg>"""

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Piper Homelab — CYBERPUNK</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}

body{
  font-family:'Inter','JetBrains Mono',system-ui,sans-serif;
  background:#08080f;
  color:#c0c0e0;
  min-height:100vh;
  overflow-x:hidden;
  position:relative;
}

/* Scanline overlay */
body::before{
  content:'';
  position:fixed;
  top:0;left:0;width:100%;height:100%;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,240,255,0.015) 2px,rgba(0,240,255,0.015) 4px);
  pointer-events:none;z-index:9999;
}

.container{max-width:1100px;margin:0 auto;padding:0.75rem}

/* ── Header ── */
.header{
  background:linear-gradient(135deg,#0d0d1a 0%,#0a0a18 100%);
  border-radius:14px;padding:0.9rem 1.25rem;margin-bottom:0.75rem;
  border:1px solid rgba(255,0,170,0.3);
  box-shadow:0 0 15px rgba(255,0,170,0.1),inset 0 0 30px rgba(0,240,255,0.03);
  position:relative;overflow:hidden;
}
.header::after{
  content:'';position:absolute;top:0;left:0;width:100%;height:1px;
  background:linear-gradient(90deg,transparent,#ff00aa,transparent);
}
.header-row{display:flex;align-items:center;justify-content:space-between}
.header-left{display:flex;align-items:center;gap:0.75rem}
.header-icon{font-size:1.4rem;filter:drop-shadow(0 0 6px rgba(0,240,255,0.4))}
h1{
  font-size:1.15rem;font-weight:700;
  background:linear-gradient(90deg,#00f0ff,#ff00aa);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;letter-spacing:-0.02em;
}
.header-right{text-align:right}
.last-update{color:#6666aa;font-size:0.65rem;font-family:'JetBrains Mono',monospace;line-height:1.3}
.status-dot{
  display:inline-block;width:7px;height:7px;border-radius:50%;
  background:#00ff41;box-shadow:0 0 8px rgba(0,255,65,0.5);
  margin-right:4px;animation:pulse 2s infinite;
}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.subtitle{color:#6666aa;font-size:0.72rem;margin-top:2px}

/* ── Tab Nav ── */
.tab-bar{
  display:flex;gap:0;margin-bottom:0.75rem;
  background:#0d0d1a;border-radius:10px;
  border:1px solid rgba(255,0,170,0.2);
  overflow:hidden;
}
.tab-btn{
  flex:1;text-align:center;
  padding:0.6rem 0.5rem;cursor:pointer;font-size:0.78rem;font-weight:500;
  color:#5555aa;transition:all 0.3s;
  border:none;background:transparent;font-family:inherit;
  position:relative;
}
.tab-btn.active{
  color:#00f0ff;
  background:rgba(0,240,255,0.05);
  text-shadow:0 0 10px rgba(0,240,255,0.3);
}
.tab-btn.active::after{
  content:'';position:absolute;bottom:0;left:10%;width:80%;height:2px;
  background:linear-gradient(90deg,transparent,#00f0ff,transparent);
}
.tab-btn:not(:last-child){border-right:1px solid rgba(255,0,170,0.15)}
.tab-btn:hover{color:#8888dd}

/* ── Tab Content ── */
.tab-content{display:none}
.tab-content.active{display:block}

/* ── Cards ── */
.card{
  background:linear-gradient(135deg,#0d0d1a 0%,#0a0a15 100%);
  border-radius:14px;padding:0.9rem 1rem;
  border:1px solid rgba(255,0,170,0.15);
  margin-bottom:0.6rem;
  box-shadow:0 0 10px rgba(255,0,170,0.05);
  transition:border-color 0.3s,box-shadow 0.3s;
}
.card:hover{
  border-color:rgba(0,240,255,0.3);
  box-shadow:0 0 20px rgba(0,240,255,0.08);
}
.card-title{
  font-size:0.72rem;font-weight:600;color:#8888cc;
  text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.6rem;
  display:flex;align-items:center;gap:0.4rem;
  font-family:'JetBrains Mono',monospace;
}

/* ── Stats Grid ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:0.6rem}
.stat-row{
  display:flex;justify-content:space-between;align-items:center;
  padding:0.35rem 0;font-size:0.72rem;
  border-bottom:1px solid rgba(255,255,255,0.03);
}
.stat-row:last-child{border-bottom:none}
.stat-label{color:#6666aa}
.stat-value{color:#c0c0e0;font-weight:500;text-align:right;font-family:'JetBrains Mono',monospace}

/* ── Bars ── */
.bar-wrap{height:3px;background:rgba(255,255,255,0.05);border-radius:2px;margin:0.2rem 0 0.35rem;overflow:hidden}
.bar-fill{height:100%;border-radius:2px;transition:width 0.5s ease}
.bar-fill.green{background:#00ff41;box-shadow:0 0 8px rgba(0,255,65,0.3)}
.bar-fill.yellow{background:#ffd700;box-shadow:0 0 8px rgba(255,215,0,0.3)}
.bar-fill.red{background:#ff0044;box-shadow:0 0 8px rgba(255,0,68,0.3)}

/* ── CT List ── */
.ct-list{font-size:0.65rem;color:#6666aa;margin-top:0.3rem;max-height:140px;overflow-y:auto;font-family:'JetBrains Mono',monospace}
.ct-list::-webkit-scrollbar{width:3px}
.ct-list::-webkit-scrollbar-thumb{background:rgba(255,0,170,0.3);border-radius:2px}
.ct-list-item{padding:0.18rem 0;border-bottom:1px solid rgba(255,255,255,0.03);display:flex;gap:0.3rem}
.ct-id{color:#444488;min-width:2rem}
.ct-name{color:#8888bb}
.ct-status{color:#00ff41}
.ct-status.stop{color:#ff0044}

/* ── Error ── */
.error-msg{color:#ff0044;font-size:0.68rem;font-style:italic;margin-bottom:0.3rem}

/* ── Datastore ── */
.ds-row{display:flex;justify-content:space-between;font-size:0.68rem;padding:0.2rem 0;border-bottom:1px solid rgba(255,255,255,0.03)}
.ds-name{color:#ff00aa}
.ds-bar{height:2px;background:rgba(255,255,255,0.05);border-radius:2px;margin:0.15rem 0;overflow:hidden}

/* ── Services Grid ── */
.services-grid{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(130px,1fr));
  gap:0.5rem;
}
.service-card{
  background:linear-gradient(135deg,#0d0d1a 0%,#0a0a15 100%);
  border:1px solid rgba(255,0,170,0.15);
  border-radius:12px;padding:0.7rem 0.5rem;
  text-align:center;text-decoration:none;color:#c0c0e0;
  transition:all 0.3s;
  position:relative;overflow:hidden;
}
.service-card::before{
  content:'';position:absolute;top:0;left:0;width:100%;height:1px;
  background:linear-gradient(90deg,transparent,#ff00aa,transparent);
  opacity:0;transition:opacity 0.3s;
}
.service-card:hover{
  border-color:#00f0ff;
  background:rgba(0,240,255,0.03);
  box-shadow:0 0 20px rgba(0,240,255,0.1);
  transform:translateY(-2px);
}
.service-card:hover::before{opacity:1}
.service-card:active{transform:scale(0.97)}
.service-icon{font-size:1.4rem;margin-bottom:0.2rem}
.service-name{font-size:0.68rem;font-weight:600}
.service-cat{font-size:0.6rem;color:#6666aa;margin-top:0.1rem;font-family:'JetBrains Mono',monospace}

/* ── Cat Colors ── */
.cat-media{color:#00f0ff}
.cat-arr{color:#ffd700}
.cat-download{color:#ff0044}
.cat-infra{color:#ff00aa}
.cat-monitor{color:#00ff41}
.cat-security{color:#ff0044}
.cat-network{color:#ff8800}
.cat-dev{color:#6666aa}
.cat-tools{color:#00f0ff}
.cat-docs{color:#6666aa}
.cat-request{color:#00ff41}
.cat-ai{color:#aa66ff}

/* ── Architecture ── */
.arch-wrap{
  background:#0d0d1a;border-radius:14px;
  border:1px solid rgba(255,0,170,0.15);
  padding:0.8rem;overflow-x:auto;
}
.arch-frame{width:100%;border:none;display:block}

/* ── Footer ── */
.footer{
  text-align:center;padding:1rem 0 0.5rem;
  color:#444477;font-size:0.65rem;
  border-top:1px solid rgba(255,0,170,0.1);margin-top:0.5rem;
  font-family:'JetBrains Mono',monospace;
}

/* ── Grid bg ── */
.container::before{
  content:'';position:fixed;top:0;left:0;width:100%;height:100%;
  background-image:
    linear-gradient(rgba(0,240,255,0.02) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,240,255,0.02) 1px,transparent 1px);
  background-size:40px 40px;
  pointer-events:none;z-index:-1;
}
</style>
</head>
<body>

<div class="container">

<!-- Header -->
<div class="header">
  <div class="header-row">
    <div class="header-left">
      <span class="header-icon">🏴</span>
      <div>
        <h1>PIPER HOMELAB</h1>
        <div class="subtitle">Anthony Piper /* Las Vegas */ 10.2.7.x/24</div>
      </div>
    </div>
    <div class="header-right">
      <div style="font-size:0.65rem;color:#8888cc"><span class="status-dot"></span>SYSTEMS ONLINE</div>
      <div class="last-update">{{ updated }}</div>
    </div>
  </div>
</div>

<!-- Tabs -->
<div class="tab-bar">
  <button class="tab-btn active" onclick="switchTab(0)">📊 OVERVIEW</button>
  <button class="tab-btn" onclick="switchTab(1)">🔗 SERVICES</button>
  <button class="tab-btn" onclick="switchTab(2)">🏗️ TOPOLOGY</button>
</div>

<!-- Tab: Overview -->
<div class="tab-content active" id="tab0">
  <div class="stats-grid">

    <!-- PVE1 -->
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
      {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}<div class="bar-wrap"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>{% endif %}
      {% endif %}
      <div class="stat-row"><span class="stat-label">Disk</span><span class="stat-value">{{ p1.disk_used or '?' }} / {{ p1.disk_total or '?' }} ({{ p1.disk_pct or '?' }})</span></div>
      <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ p1.uptime or '—' }}</span></div>
      {% if p1.cts %}
      <div class="ct-list">
        <div style="color:#6666aa;font-size:0.65rem;margin-bottom:0.25rem;font-family:'JetBrains Mono',monospace">// CONTAINERS</div>
        {% for ct in p1.cts %}
        <div class="ct-list-item"><span class="ct-id">{{ ct.split('|')[0].strip() }}</span><span class="ct-name">{{ ct.split('|')[1].strip() }}</span><span class="ct-status{{ ' stop' if ct.split('|')[2].strip() != 'running' else '' }}">{{ ct.split('|')[2].strip() }}</span></div>
        {% endfor %}
      </div>
      {% endif %}
    </div>

    <!-- PVE2 -->
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
      {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}<div class="bar-wrap"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>{% endif %}
      {% endif %}
      <div class="stat-row"><span class="stat-label">Disk</span><span class="stat-value">{{ p2.disk_used or '?' }} / {{ p2.disk_total or '?' }} ({{ p2.disk_pct or '?' }})</span></div>
      <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ p2.uptime or '—' }}</span></div>
      {% if p2.cts %}
      <div class="ct-list">
        <div style="color:#6666aa;font-size:0.65rem;margin-bottom:0.25rem;font-family:'JetBrains Mono',monospace">// CONTAINERS</div>
        {% for ct in p2.cts %}
        <div class="ct-list-item"><span class="ct-id">{{ ct.split('|')[0].strip() }}</span><span class="ct-name">{{ ct.split('|')[1].strip() }}</span><span class="ct-status{{ ' stop' if ct.split('|')[2].strip() != 'running' else '' }}">{{ ct.split('|')[2].strip() }}</span></div>
        {% endfor %}
      </div>
      {% endif %}
    </div>

    <!-- PBS -->
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
      {% if mt > 0 %}{% set mp = (mu / mt * 100)|round %}<div class="bar-wrap"><div class="bar-fill {{ 'green' if mp < 70 else 'yellow' if mp < 90 else 'red' }}" style="width:{{ mp }}%"></div></div>{% endif %}
      {% endif %}
      <div class="stat-row"><span class="stat-label">Boot</span><span class="stat-value">{{ pbs.boot_used or '?' }} / {{ pbs.boot_total or '?' }} ({{ pbs.boot_pct or '?' }})</span></div>
      <div class="stat-row"><span class="stat-label">Uptime</span><span class="stat-value">{{ pbs.uptime or '—' }}</span></div>
      {% if pbs.datastores %}
      <div style="margin-top:0.5rem;font-size:0.65rem;color:#6666aa;margin-bottom:0.25rem;font-family:'JetBrains Mono',monospace">// DATASTORES</div>
      {% for ds in pbs.datastores %}
      <div class="ds-row"><span class="ds-name">{{ ds.name }}</span><span style="color:#c0c0e0">{{ ds.used }} / {{ ds.total }} ({{ ds.pct }})</span></div>
      <div class="ds-bar"><div class="bar-fill {{ ds.bar }}" style="width:{{ ds.pct.replace('%','') }}%"></div></div>
      {% endfor %}
      {% endif %}
    </div>

  </div>
</div>

<!-- Tab: Services -->
<div class="tab-content" id="tab1">
<div class="services-grid">
{% for s in services %}
<a class="service-card" href="{{ s.url }}" target="_blank">
<div class="service-icon">{{ s.icon }}</div>
<div class="service-name">{{ s.name }}</div>
<div class="service-cat {{ s.cat }}">[{{ s.cat }}]</div>
</a>
{% endfor %}
</div>
</div>

<!-- Tab: Architecture -->
<div class="tab-content" id="tab2">
<div class="arch-wrap">
<img src="/arch" alt="Homelab Topology" class="arch-frame" />
</div>
</div>

<div class="footer">// POWERED BY HERMES AGENT · v4.0 · CT 100 (10.2.7.x) //</div>
</div>

<script>
function switchTab(n){
document.querySelectorAll('.tab-btn').forEach(t=>t.classList.remove('active'));
document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
document.querySelectorAll('.tab-btn')[n].classList.add('active');
document.getElementById('tab'+n).classList.add('active');
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
