#!/usr/bin/env python3
"""Media Dashboard — Jellyfin recently added + request movies, TV, music, books via *arr APIs"""

import os, json, urllib.request, urllib.parse, time, re
from flask import Flask, render_template_string, request

app = Flask(__name__)

# ─── Config ─────────────────────────────────────────────────────
MEDIA_HOST = "10.2.7.109"

# API keys
RADARR_KEY = "7d50365cc0934669b0aac6f9f7415688"
SONARR_KEY = "40e5a97c2c7c47c8a13ad6fa7d9324fa"
LIDARR_KEY = "935c193b61e640898c520a7e1c5bb5a6"
READARR_KEY = "ad9edb79876f4107a9de7472259e212b"

# Ports
RADARR_PORT = 7878
SONARR_PORT = 8989
LIDARR_PORT = 8686
READARR_PORT = 8787

BASE = f"http://{MEDIA_HOST}"

# ─── API helpers ────────────────────────────────────────────────
def api_get(url):
    try:
        r = urllib.request.urlopen(url, timeout=10)
        return json.loads(r.read())
    except Exception as e:
        print(f"API GET error: {e}")
        return None

def api_post(url, data):
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read())
    except Exception as e:
        print(f"API POST error: {e}")
        return None

# ─── Data fetch functions ──────────────────────────────────────
def get_recent_movies(limit=12):
    data = api_get(f"{BASE}:{RADARR_PORT}/api/v3/history?pageSize=50&sortKey=date&sortDirection=descending&eventType=3&apiKey={RADARR_KEY}")
    if not data: return []
    movies, seen = [], set()
    for r in data.get("records", []):
        m = r.get("movie", {})
        mid = m.get("id")
        if mid and mid not in seen:
            seen.add(mid)
            movies.append({"title": m.get("title", "?"), "year": m.get("year", "?"), "added": (r.get("date", "") or "")[:10], "type": "movie"})
    return movies[:limit]

def get_recent_tv(limit=12):
    data = api_get(f"{BASE}:{SONARR_PORT}/api/v3/history?pageSize=50&sortKey=date&sortDirection=descending&eventType=3&apiKey={SONARR_KEY}")
    if not data: return []
    tv, seen = [], set()
    for r in data.get("records", []):
        s = r.get("series", {})
        sid = s.get("id")
        if sid and sid not in seen:
            seen.add(sid)
            tv.append({"title": s.get("title", "?"), "year": "", "added": (r.get("date", "") or "")[:10], "type": "tv"})
    return tv[:limit]

def get_recent_music(limit=12):
    data = api_get(f"{BASE}:{LIDARR_PORT}/api/v1/artist?sortKey=lastAlbum&sortDirection=descending&apiKey={LIDARR_KEY}")
    if not data: return []
    music = []
    for a in data[:limit]:
        if a.get("lastAlbum"):
            music.append({"title": a.get("artistName", "?"), "year": a.get("lastAlbum", {}).get("title", ""), "added": (a.get("added", "") or "")[:10], "type": "music"})
        else:
            music.append({"title": a.get("artistName", "?"), "year": "", "added": (a.get("added", "") or "")[:10], "type": "music"})
    return music[:limit]

def get_recent_books(limit=12):
    # Readarr recently added via history
    data = api_get(f"{BASE}:{READARR_PORT}/api/v1/author?sortKey=lastBook&sortDirection=descending&apiKey={READARR_KEY}")
    if not data: return []
    books = []
    for a in data[:limit]:
        books.append({"title": a.get("authorName", "?"), "year": "", "added": (a.get("added", "") or "")[:10], "type": "book"})
    return books[:limit]

def get_queue():
    items = []
    for port, key, label in [(RADARR_PORT, RADARR_KEY, "movie"), (SONARR_PORT, SONARR_KEY, "tv"), (LIDARR_PORT, LIDARR_KEY, "music"), (READARR_PORT, READARR_KEY, "book")]:
        data = api_get(f"{BASE}:{port}/api/v1/queue?pageSize=10&apiKey={key}")
        if data and "records" in data:
            for r in data["records"]:
                title = r.get("title", r.get("series", {}).get("title", r.get("artist", {}).get("artistName", r.get("author", {}).get("authorName", "?"))))
                items.append({"title": title, "status": r.get("status", "?"), "type": label})
    return items

def search_movie(query):
    data = api_get(f"{BASE}:{RADARR_PORT}/api/v3/movie/lookup?term={urllib.parse.quote(query)}&apiKey={RADARR_KEY}")
    if not data: return []
    existing = api_get(f"{BASE}:{RADARR_PORT}/api/v3/movie?apiKey={RADARR_KEY}")
    existing_ids = {m.get("tmdbId") for m in (existing or []) if m.get("tmdbId")}
    results = []
    for m in data[:10]:
        results.append({"title": m.get("title", "?"), "year": m.get("year", "?"), "id": m.get("tmdbId") or m.get("id"), "type": "movie", "exists": m.get("tmdbId") in existing_ids})
    return results

def search_tv(query):
    data = api_get(f"{BASE}:{SONARR_PORT}/api/v3/series/lookup?term={urllib.parse.quote(query)}&apiKey={SONARR_KEY}")
    if not data: return []
    existing = api_get(f"{BASE}:{SONARR_PORT}/api/v3/series?apiKey={SONARR_KEY}")
    existing_ids = {s.get("tvdbId") for s in (existing or []) if s.get("tvdbId")}
    results = []
    for s in data[:10]:
        tid = s.get("tvdbId") or s.get("tvRageId")
        results.append({"title": s.get("title", "?"), "year": s.get("year", "?"), "id": tid, "type": "tv", "exists": tid in existing_ids})
    return results

def search_music(query):
    data = api_get(f"{BASE}:{LIDARR_PORT}/api/v1/artist/lookup?term={urllib.parse.quote(query)}&apiKey={LIDARR_KEY}")
    if not data: return []
    existing = api_get(f"{BASE}:{LIDARR_PORT}/api/v1/artist?apiKey={LIDARR_KEY}")
    existing_ids = {a.get("foreignArtistId") for a in (existing or []) if a.get("foreignArtistId")}
    results = []
    for a in data[:10]:
        results.append({"title": a.get("artistName", "?"), "year": a.get("disambiguation", ""), "id": a.get("foreignArtistId"), "type": "music", "exists": a.get("foreignArtistId") in existing_ids})
    return results

def search_books(query):
    data = api_get(f"{BASE}:{READARR_PORT}/api/v1/author/lookup?term={urllib.parse.quote(query)}&apiKey={READARR_KEY}")
    if not data: return []
    existing = api_get(f"{BASE}:{READARR_PORT}/api/v1/author?apiKey={READARR_KEY}")
    existing_ids = {a.get("foreignAuthorId") for a in (existing or []) if a.get("foreignAuthorId")}
    results = []
    for a in data[:10]:
        results.append({"title": a.get("authorName", "?"), "year": "", "id": a.get("foreignAuthorId"), "type": "book", "exists": a.get("foreignAuthorId") in existing_ids})
    return results

def add_movie(tmdb_id, title, year):
    data = api_get(f"{BASE}:{RADARR_PORT}/api/v3/movie/lookup?term=tmdb:{tmdb_id}&apiKey={RADARR_KEY}")
    if not data or len(data) == 0: return False, f"Couldn't find {title}"
    movie = data[0]
    add_data = {"title": movie["title"], "tmdbId": movie.get("tmdbId"), "year": movie.get("year"),
        "qualityProfileId": 1, "rootFolderPath": "/data/media/movies", "monitored": True,
        "addOptions": {"searchForMovie": True}}
    result = api_post(f"{BASE}:{RADARR_PORT}/api/v3/movie?apiKey={RADARR_KEY}", add_data)
    return bool(result), f"Added {title} ({year})" if result else f"Failed to add {title}"

def add_tv(tvdb_id, title, year):
    data = api_get(f"{BASE}:{SONARR_PORT}/api/v3/series/lookup?term=tvdb:{tvdb_id}&apiKey={SONARR_KEY}")
    if not data or len(data) == 0: return False, f"Couldn't find {title}"
    tv = data[0]
    add_data = {"title": tv["title"], "tvdbId": tv.get("tvdbId"), "year": tv.get("year"),
        "qualityProfileId": 1, "languageProfileId": 1, "rootFolderPath": "/data/media/tv",
        "monitored": True, "seasons": [{"seasonNumber": s.get("seasonNumber"), "monitored": True} for s in tv.get("seasons", [])],
        "addOptions": {"searchForMissingEpisodes": True}}
    result = api_post(f"{BASE}:{SONARR_PORT}/api/v3/series?apiKey={SONARR_KEY}", add_data)
    return bool(result), f"Added {title} ({year})" if result else f"Failed to add {title}"

def add_artist(foreign_id, title):
    data = api_get(f"{BASE}:{LIDARR_PORT}/api/v1/artist/lookup?term=foreignArtistId:{foreign_id}&apiKey={LIDARR_KEY}")
    if not data or len(data) == 0: return False, f"Couldn't find {title}"
    artist = data[0]
    add_data = {"artistName": artist["artistName"], "foreignArtistId": artist.get("foreignArtistId"),
        "qualityProfileId": 1, "metadataProfileId": 1, "rootFolderPath": "/data/media/music",
        "monitored": True, "addOptions": {"searchForNewAlbum": True}}
    result = api_post(f"{BASE}:{LIDARR_PORT}/api/v1/artist?apiKey={LIDARR_KEY}", add_data)
    return bool(result), f"Added {title}" if result else f"Failed to add {title}"

def add_author(foreign_id, title):
    data = api_get(f"{BASE}:{READARR_PORT}/api/v1/author/lookup?term=foreignAuthorId:{foreign_id}&apiKey={READARR_KEY}")
    if not data or len(data) == 0: return False, f"Couldn't find {title}"
    author = data[0]
    add_data = {"authorName": author["authorName"], "foreignAuthorId": author.get("foreignAuthorId"),
        "qualityProfileId": 1, "metadataProfileId": 1, "rootFolderPath": "/data/media/books",
        "monitored": True, "addOptions": {"searchForNewBook": True}}
    result = api_post(f"{BASE}:{READARR_PORT}/api/v1/author?apiKey={READARR_KEY}", add_data)
    return bool(result), f"Added {title}" if result else f"Failed to add {title}"

# ─── HTML Template ─────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Media Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#020617;min-height:100vh;padding:2rem;color:white}
.container{max-width:1100px;margin:0 auto}
h1{font-size:1.5rem;font-weight:700;margin-bottom:0.25rem}
.subtitle{color:#64748b;font-size:0.8rem;margin-bottom:2rem}
.tabs{display:flex;gap:0.25rem;margin-bottom:1.5rem;border-bottom:1px solid #1e293b;overflow-x:auto;padding-bottom:0}
.tab{padding:0.6rem 1rem;cursor:pointer;font-size:0.75rem;color:#64748b;border:1px solid transparent;border-bottom:none;border-radius:0.5rem 0.5rem 0 0;transition:all 0.2s;white-space:nowrap}
.tab:hover{color:#e2e8f0}
.tab.active{color:#22d3ee;border-color:#1e293b;background:rgba(15,23,42,0.5)}
.tab-content{display:none}
.tab-content.active{display:block}
.card{background:rgba(15,23,42,0.5);border:1px solid #1e293b;border-radius:0.75rem;padding:1.25rem;margin-bottom:1rem}
.card h2{font-size:0.85rem;margin-bottom:0.75rem;color:#94a3b8}
.media-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0.75rem}
.media-item{background:rgba(0,0,0,0.3);border:1px solid #1e293b;border-radius:0.5rem;padding:0.75rem;transition:border-color 0.2s}
.media-item:hover{border-color:#22d3ee}
.media-title{font-size:0.8rem;font-weight:600;margin-bottom:0.25rem}
.media-meta{font-size:0.65rem;color:#64748b}
.badge{display:inline-block;padding:0.125rem 0.4rem;border-radius:999px;font-size:0.55rem;font-weight:600}
.badge.movie{background:rgba(34,211,238,0.2);color:#22d3ee}
.badge.tv{background:rgba(251,191,36,0.2);color:#fbbf24}
.badge.music{background:rgba(167,139,250,0.2);color:#a78bfa}
.badge.book{background:rgba(52,211,153,0.2);color:#34d399}
input[type=text],select{width:100%;padding:0.5rem 0.75rem;background:rgba(15,23,42,0.5);border:1px solid #1e293b;border-radius:0.5rem;color:white;font-family:inherit;font-size:0.8rem}
input[type=text]:focus,select:focus{outline:none;border-color:#22d3ee}
.btn{padding:0.4rem 1.2rem;border:1px solid #22d3ee;border-radius:0.5rem;background:transparent;color:#22d3ee;font-family:inherit;font-size:0.75rem;cursor:pointer;transition:all 0.2s;white-space:nowrap}
.btn:hover{background:rgba(34,211,238,0.1)}
.btn:disabled{opacity:0.4;cursor:not-allowed}
.btn.success{border-color:#34d399;color:#34d399}.btn.success:hover{background:rgba(52,211,153,0.1)}
.btn.danger{border-color:#fb7185;color:#fb7185}
.search-row{display:flex;gap:0.5rem;margin-bottom:1rem;align-items:center}
.search-row input{flex:1}
.search-row select{width:auto;min-width:100px}
.result-item{display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0;border-bottom:1px solid #1e293b}
.result-item:last-child{border-bottom:none}
.result-info{font-size:0.8rem}
.result-title{font-weight:600}
.result-year{color:#64748b;font-size:0.7rem}
.msg{padding:0.5rem;border-radius:0.5rem;font-size:0.75rem;margin-bottom:0.75rem}
.msg.ok{background:rgba(34,211,238,0.1);border:1px solid #22d3ee;color:#22d3ee}
.msg.err{background:rgba(251,113,133,0.1);border:1px solid #fb7185;color:#fb7185}
.msg.info{background:rgba(251,191,36,0.1);border:1px solid #fbbf24;color:#fbbf24}
.footer{margin-top:2rem;color:#475569;font-size:0.7rem;text-align:center}
.queue-list{font-size:0.75rem}
.queue-item{padding:0.4rem 0;border-bottom:1px solid #1e293b;display:flex;justify-content:space-between}
</style>
</head>
<body>
<div class="container">
<h1>📺 Media Dashboard</h1>
<p class="subtitle">Piper Homelab · Radarr + Sonarr + Lidarr + Readarr</p>

{% if msg %}
<div class="msg {{ msg.type }}">{{ msg.text }}</div>
{% endif %}

<div class="tabs">
  <div class="tab {{ 'active' if tab == 'recent' }}" onclick="switchTab('recent')">📋 Recent</div>
  <div class="tab {{ 'active' if tab == 'request-movie' }}" onclick="switchTab('request-movie')">🎬 Movies</div>
  <div class="tab {{ 'active' if tab == 'request-tv' }}" onclick="switchTab('request-tv')">📺 TV</div>
  <div class="tab {{ 'active' if tab == 'request-music' }}" onclick="switchTab('request-music')">🎵 Music</div>
  <div class="tab {{ 'active' if tab == 'request-book' }}" onclick="switchTab('request-book')">📖 Books</div>
  <div class="tab {{ 'active' if tab == 'queue' }}" onclick="switchTab('queue')">⏳ Queue</div>
</div>

<!-- Recently Added Tab -->
<div id="tab-recent" class="tab-content {{ 'active' if tab == 'recent' }}">
  <div class="card"><h2>🎬 Recently Added Movies</h2>
    {% if recent_movies %}<div class="media-grid">
      {% for m in recent_movies %}<div class="media-item"><div class="media-title">{{ m.title }}</div><div class="media-meta">{{ m.year }} · <span class="badge movie">Movie</span> · {{ m.added }}</div></div>{% endfor %}
    </div>{% else %}<p style="color:#64748b;font-size:0.75rem;">None</p>{% endif %}
  </div>
  <div class="card"><h2>📺 Recently Added TV</h2>
    {% if recent_tv %}<div class="media-grid">
      {% for s in recent_tv %}<div class="media-item"><div class="media-title">{{ s.title }}</div><div class="media-meta"><span class="badge tv">TV</span> · {{ s.added }}</div></div>{% endfor %}
    </div>{% else %}<p style="color:#64748b;font-size:0.75rem;">None</p>{% endif %}
  </div>
  <div class="card"><h2>🎵 Recently Added Music</h2>
    {% if recent_music %}<div class="media-grid">
      {% for a in recent_music %}<div class="media-item"><div class="media-title">{{ a.title }}</div><div class="media-meta">{{ a.year }} · <span class="badge music">Music</span> · {{ a.added }}</div></div>{% endfor %}
    </div>{% else %}<p style="color:#64748b;font-size:0.75rem;">None</p>{% endif %}
  </div>
  <div class="card"><h2>📖 Recently Added Books</h2>
    {% if recent_books %}<div class="media-grid">
      {% for b in recent_books %}<div class="media-item"><div class="media-title">{{ b.title }}</div><div class="media-meta"><span class="badge book">Book</span> · {{ b.added }}</div></div>{% endfor %}
    </div>{% else %}<p style="color:#64748b;font-size:0.75rem;">None</p>{% endif %}
  </div>
</div>

<!-- Movie Request Tab -->
<div id="tab-request-movie" class="tab-content {{ 'active' if tab == 'request-movie' }}">
  <div class="card"><h2>🔍 Search Movies</h2>
    <form method="POST" action="/search"><input type="hidden" name="type" value="movie">
      <div class="search-row"><input type="text" name="query" placeholder="Search movies..." value="{{ query }}"><button class="btn" type="submit">Search</button></div>
    </form>
    {% if results_movie %}<h2>Results</h2>
      {% for r in results_movie %}<div class="result-item"><div class="result-info"><span class="result-title">{{ r.title }}</span> <span class="result-year">{{ r.year }}</span></div>
        <div>{% if r.exists %}<span class="badge movie">Have it</span>{% else %}<form method="POST" action="/add" style="display:inline"><input type="hidden" name="type" value="movie"><input type="hidden" name="id" value="{{ r.id }}"><input type="hidden" name="title" value="{{ r.title }}"><input type="hidden" name="year" value="{{ r.year }}"><button class="btn success" type="submit">+ Add</button></form>{% endif %}</div>
      </div>{% endfor %}
    {% endif %}
  </div>
</div>

<!-- TV Request Tab -->
<div id="tab-request-tv" class="tab-content {{ 'active' if tab == 'request-tv' }}">
  <div class="card"><h2>🔍 Search TV Shows</h2>
    <form method="POST" action="/search"><input type="hidden" name="type" value="tv">
      <div class="search-row"><input type="text" name="query" placeholder="Search TV..." value="{{ query }}"><button class="btn" type="submit">Search</button></div>
    </form>
    {% if results_tv %}<h2>Results</h2>
      {% for r in results_tv %}<div class="result-item"><div class="result-info"><span class="result-title">{{ r.title }}</span> <span class="result-year">{{ r.year }}</span></div>
        <div>{% if r.exists %}<span class="badge tv">Have it</span>{% else %}<form method="POST" action="/add" style="display:inline"><input type="hidden" name="type" value="tv"><input type="hidden" name="id" value="{{ r.id }}"><input type="hidden" name="title" value="{{ r.title }}"><input type="hidden" name="year" value="{{ r.year }}"><button class="btn success" type="submit">+ Add</button></form>{% endif %}</div>
      </div>{% endfor %}
    {% endif %}
  </div>
</div>

<!-- Music Request Tab -->
<div id="tab-request-music" class="tab-content {{ 'active' if tab == 'request-music' }}">
  <div class="card"><h2>🔍 Search Artists</h2>
    <form method="POST" action="/search"><input type="hidden" name="type" value="music">
      <div class="search-row"><input type="text" name="query" placeholder="Search artists..." value="{{ query }}"><button class="btn" type="submit">Search</button></div>
    </form>
    {% if results_music %}<h2>Results</h2>
      {% for r in results_music %}<div class="result-item"><div class="result-info"><span class="result-title">{{ r.title }}</span></div>
        <div>{% if r.exists %}<span class="badge music">Have it</span>{% else %}<form method="POST" action="/add" style="display:inline"><input type="hidden" name="type" value="music"><input type="hidden" name="id" value="{{ r.id }}"><input type="hidden" name="title" value="{{ r.title }}"><button class="btn success" type="submit">+ Add</button></form>{% endif %}</div>
      </div>{% endfor %}
    {% endif %}
  </div>
</div>

<!-- Book Request Tab -->
<div id="tab-request-book" class="tab-content {{ 'active' if tab == 'request-book' }}">
  <div class="card"><h2>🔍 Search Authors</h2>
    <form method="POST" action="/search"><input type="hidden" name="type" value="book">
      <div class="search-row"><input type="text" name="query" placeholder="Search authors..." value="{{ query }}"><button class="btn" type="submit">Search</button></div>
    </form>
    {% if results_book %}<h2>Results</h2>
      {% for r in results_book %}<div class="result-item"><div class="result-info"><span class="result-title">{{ r.title }}</span></div>
        <div>{% if r.exists %}<span class="badge book">Have it</span>{% else %}<form method="POST" action="/add" style="display:inline"><input type="hidden" name="type" value="book"><input type="hidden" name="id" value="{{ r.id }}"><input type="hidden" name="title" value="{{ r.title }}"><button class="btn success" type="submit">+ Add</button></form>{% endif %}</div>
      </div>{% endfor %}
    {% endif %}
  </div>
</div>

<!-- Queue Tab -->
<div id="tab-queue" class="tab-content {{ 'active' if tab == 'queue' }}">
  <div class="card"><h2>⏳ Download Queue</h2>
    {% if queue %}<div class="queue-list">
      {% for q in queue %}<div class="queue-item"><span>{{ q.title }} <span class="badge {{ q.type }}">{{ q.type|upper }}</span></span><span>{{ q.status }}</span></div>{% endfor %}
    </div>{% else %}<p style="color:#64748b;font-size:0.75rem;">Queue is empty</p>{% endif %}
  </div>
</div>

<p class="footer">Piper Homelab · CT 103 · Auto-refresh every 60s</p>
</div>

<script>
function switchTab(name){
document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
document.querySelector('.tab[onclick*="'+name+'"]').classList.add('active');
document.getElementById('tab-'+name).classList.add('active');
}
</script>
</body></html>"""

@app.route("/")
def index(tab="recent", query="", results_movie=None, results_tv=None, results_music=None, results_book=None, msg=None):
    return render_template_string(HTML, tab=tab,
        recent_movies=get_recent_movies(), recent_tv=get_recent_tv(),
        recent_music=get_recent_music(), recent_books=get_recent_books(),
        queue=get_queue(),
        query=query,
        results_movie=results_movie or [],
        results_tv=results_tv or [],
        results_music=results_music or [],
        results_book=results_book or [],
        msg=msg)

@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query", "").strip()
    med_type = request.form.get("type", "movie")
    if not query:
        return index(msg={"type": "err", "text": "❌ Enter a search term"})
    
    results = []
    if med_type == "movie": results = search_movie(query)
    elif med_type == "tv": results = search_tv(query)
    elif med_type == "music": results = search_music(query)
    elif med_type == "book": results = search_books(query)
    
    if not results:
        return index(tab=f"request-{med_type}", query=query,
            msg={"type": "info", "text": f"No results for '{query}'"})
    
    kwargs = {"tab": f"request-{med_type}", "query": query}
    if med_type == "movie": kwargs["results_movie"] = results
    elif med_type == "tv": kwargs["results_tv"] = results
    elif med_type == "music": kwargs["results_music"] = results
    elif med_type == "book": kwargs["results_book"] = results
    return index(**kwargs)

@app.route("/add", methods=["POST"])
def add():
    med_type = request.form.get("type")
    item_id = request.form.get("id")
    title = request.form.get("title", "?")
    year = request.form.get("year", "")
    
    ok, msg_text = False, "Unknown type"
    if med_type == "movie": ok, msg_text = add_movie(item_id, title, year)
    elif med_type == "tv": ok, msg_text = add_tv(item_id, title, year)
    elif med_type == "music": ok, msg_text = add_artist(item_id, title)
    elif med_type == "book": ok, msg_text = add_author(item_id, title)
    
    msg = {"type": "ok", "text": f"✅ {msg_text}"} if ok else {"type": "err", "text": f"❌ {msg_text}"}
    return index(msg=msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5051, debug=False, threaded=True)