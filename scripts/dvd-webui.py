#!/usr/bin/env python3
"""DVD Ripping Web UI — Flask app for Hermes CT 103 (ripper)"""

import os
import subprocess
import time
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

DEVICE = "/dev/sr0"
MOVIES_DIR = "/media/movies"
LOG_FILE = "/var/log/rip-dvd-auto.log"
RIP_LOG = "/var/log/rip-constantine.log"

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DVD Ripper</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'JetBrains Mono', monospace; background: #020617; min-height: 100vh; padding: 2rem; color: white; }
    .container { max-width: 900px; margin: 0 auto; }
    h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.25rem; }
    .subtitle { color: #64748b; font-size: 0.8rem; margin-bottom: 2rem; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }
    .card { background: rgba(15,23,42,0.5); border: 1px solid #1e293b; border-radius: 0.75rem; padding: 1.25rem; }
    .card.full { grid-column: 1 / -1; }
    .card h2 { font-size: 0.85rem; margin-bottom: 0.75rem; color: #94a3b8; }
    .stat { display: flex; justify-content: space-between; padding: 0.35rem 0; border-bottom: 1px solid #1e293b; font-size: 0.8rem; }
    .stat:last-child { border-bottom: none; }
    .label { color: #64748b; }
    .value { color: #e2e8f0; }
    .badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 999px; font-size: 0.65rem; font-weight: 600; }
    .badge.ready { background: rgba(34,211,238,0.2); color: #22d3ee; }
    .badge.ripping { background: rgba(251,191,36,0.2); color: #fbbf24; animation: pulse 2s infinite; }
    .badge.empty { background: rgba(100,116,139,0.2); color: #64748b; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
    .btn { padding: 0.5rem 1.5rem; border: 1px solid #22d3ee; border-radius: 0.5rem; background: transparent; color: #22d3ee; font-family: inherit; font-size: 0.8rem; cursor: pointer; transition: all 0.2s; }
    .btn:hover { background: rgba(34,211,238,0.1); }
    .btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn.danger { border-color: #fb7185; color: #fb7185; }
    .btn.danger:hover { background: rgba(251,113,133,0.1); }
    input[type=text] { width: 100%; padding: 0.5rem 0.75rem; background: rgba(15,23,42,0.5); border: 1px solid #1e293b; border-radius: 0.5rem; color: white; font-family: inherit; font-size: 0.8rem; margin-bottom: 0.75rem; }
    input[type=text]:focus { outline: none; border-color: #22d3ee; }
    .log-box { background: rgba(0,0,0,0.3); border: 1px solid #1e293b; border-radius: 0.5rem; padding: 0.75rem; font-size: 0.7rem; color: #94a3b8; max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
    .form-row { display: flex; gap: 0.5rem; align-items: flex-start; }
    .form-row input { flex: 1; margin-bottom: 0; }
    .msg { padding: 0.5rem; border-radius: 0.5rem; font-size: 0.75rem; margin-bottom: 0.75rem; }
    .msg.ok { background: rgba(34,211,238,0.1); border: 1px solid #22d3ee; color: #22d3ee; }
    .msg.err { background: rgba(251,113,133,0.1); border: 1px solid #fb7185; color: #fb7185; }
    .footer { margin-top: 2rem; color: #475569; font-size: 0.7rem; text-align: center; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🎬 DVD Ripper</h1>
    <p class="subtitle">CT 103 · PVE2 · HandBrakeCLI</p>

    {% if msg %}
    <div class="msg {{ msg.type }}">{{ msg.text }}</div>
    {% endif %}

    <div class="grid">
      <div class="card">
        <h2>📀 Drive Status</h2>
        <div class="stat"><span class="label">Disc</span><span class="value"><span class="badge {{ 'ready' if has_disc else 'empty' }}">{{ 'READY' if has_disc else 'EMPTY' }}</span></span></div>
        {% if has_disc %}
        <div class="stat"><span class="label">Title</span><span class="value">{{ disc_title }}</span></div>
        <div class="stat"><span class="label">Duration</span><span class="value">{{ main_title_len }}</span></div>
        {% endif %}
      </div>
      <div class="card">
        <h2>⚙️ Status</h2>
        <div class="stat"><span class="label">Rip Running</span><span class="value"><span class="badge {{ 'ripping' if is_ripping else 'empty' }}">{{ 'RIPPING' if is_ripping else 'IDLE' }}</span></span></div>
        <div class="stat"><span class="label">Last Rip</span><span class="value">{{ last_rip }}</span></div>
      </div>
    </div>

    <div class="card full">
      <h2>🎯 Rip DVD</h2>
      <form method="POST" action="/rip">
        <div class="form-row">
          <input type="text" name="movie_name" placeholder="Movie Name (Year)" value="{{ suggested_name }}" {% if not has_disc or is_ripping %}disabled{% endif %}>
          <button class="btn" type="submit" {% if not has_disc or is_ripping %}disabled{% endif %}>Rip</button>
        </div>
      </form>
    </div>

    <div class="card full">
      <h2>📋 Log</h2>
      <div class="log-box">{{ log_text }}</div>
      <div style="margin-top: 0.5rem; text-align: right;">
        <form method="POST" action="/clear-log" style="display:inline">
          <button class="btn danger" type="submit">Clear Log</button>
        </form>
        <form method="POST" action="/refresh" style="display:inline">
          <button class="btn" type="submit">Refresh</button>
        </form>
      </div>
    </div>

    <p class="footer">Piper Homelab · Hermes CT 103</p>
  </div>
</body>
</html>"""

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ""

def check_disc():
    out = run(["lsdvd", DEVICE, "-q"], timeout=15)
    if "Disc Title:" in out:
        title = ""
        for line in out.split("\n"):
            if "Disc Title:" in line:
                title = line.split("Title:")[-1].strip()
            if "Longest track:" in line:
                main_t = line.split(":")[-1].strip()
        # Get main title length
        for line in out.split("\n"):
            if line.startswith(f"Title: {main_t},"):
                len_str = line.split("Length:")[-1].split(",")[0].strip()
                return True, title, len_str
        return True, title, "?"
    return False, "", ""

def is_ripping():
    r = subprocess.run(["pgrep", "-f", "HandBrakeCLI"], capture_output=True)
    return r.returncode == 0

def read_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            lines = f.readlines()
            return "".join(lines[-30:])
    return "No log yet"

def get_last_rip():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            lines = f.readlines()
            for line in reversed(lines):
                if "✅ Rip complete" in line:
                    return line.split("]")[-1].strip() if "]" in line else "Yes"
                if "📀 Disc ejected" in line:
                    return "Completed"
    return "Never"

@app.route("/")
def index():
    has_disc, disc_title, main_len = check_disc()
    return render_template_string(HTML,
        has_disc=has_disc,
        disc_title=disc_title,
        main_title_len=main_len,
        is_ripping=is_ripping(),
        log_text=read_log(),
        last_rip=get_last_rip(),
        suggested_name=disc_title,
        msg=None)

@app.route("/rip", methods=["POST"])
def rip():
    name = request.form.get("movie_name", "").strip()
    if not name:
        return render_template_string(HTML,
            has_disc=check_disc()[0],
            disc_title=check_disc()[1],
            main_title_len=check_disc()[2],
            is_ripping=is_ripping(),
            log_text=read_log(),
            last_rip=get_last_rip(),
            suggested_name="",
            msg={"type": "err", "text": "❌ Enter a movie name"})

    if is_ripping():
        return render_template_string(HTML,
            has_disc=check_disc()[0],
            disc_title=check_disc()[1],
            main_title_len=check_disc()[2],
            is_ripping=True,
            log_text=read_log(),
            last_rip=get_last_rip(),
            suggested_name=name,
            msg={"type": "err", "text": "❌ Already ripping!"})

    subprocess.Popen(["systemd-run", "--unit=rip-web", "--same-dir",
        "/usr/local/bin/rip-dvd", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    time.sleep(2)
    return render_template_string(HTML,
        has_disc=check_disc()[0],
        disc_title=check_disc()[1],
        main_title_len=check_disc()[2],
        is_ripping=is_ripping(),
        log_text=read_log(),
        last_rip=get_last_rip(),
        suggested_name="",
        msg={"type": "ok", "text": f"🎬 Ripping {name}!"})

@app.route("/clear-log", methods=["POST"])
def clear_log():
    if os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
    return render_template_string(HTML,
        has_disc=check_disc()[0],
        disc_title=check_disc()[1],
        main_title_len=check_disc()[2],
        is_ripping=is_ripping(),
        log_text="Log cleared",
        last_rip=get_last_rip(),
        suggested_name=check_disc()[1],
        msg={"type": "ok", "text": "Log cleared"})

@app.route("/refresh", methods=["POST"])
def refresh():
    return index()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)