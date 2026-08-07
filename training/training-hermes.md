# Hermes Agent (AI Assistant) Beginner's Manual — Anthony's Homelab

*Tailored to your actual setup.*

---

## Section 1: What Hermes Agent Actually Is (the mental model)

**Think of Hermes Agent as a smart, helpful friend who lives on your homelab — you can talk to it in plain English and it can do things on your computers for you.**

Hermes (also called **Hermie** by Anthony) is an AI assistant made by Nous Research. Unlike ChatGPT or Claude that just answer questions, Hermes has **tools** — it can run commands on servers, read and edit files, search through documents, browse the web, and manage your homelab infrastructure — all through natural conversation.

**What makes Anthony's setup special:**
- Hermes runs on **CT100** — a dedicated Proxmox container
- It's accessible three ways:
  1. **Discord** — chat with Hermes in a Discord server
  2. **CLI** — talk to it directly from the terminal
  3. **Web API** — integrate it with other homelab tools
- It has **skills** (pre-built workflows for common tasks) and **memory** (remembers past conversations)
- Hermes uses **Ollama** on CT113 for local AI inference — no external API needed
- It manages the entire homelab: check service status, restart containers, update configurations, troubleshoot problems

---

## Section 2: Getting In

**Access methods:**

### Discord
- Invite Hermes bot to your Discord server
- Send direct messages or use it in channels
- Prefix commands if needed (configurable)
- Anthony calls it "Hermie" in conversation

### CLI (Direct Terminal Access)
```bash
# Start an interactive Hermes session
hermes

# Run a single command
hermes "check the status of all homelab services"

# Run with a specific profile
hermes --profile default

# List available skills
hermes skills list
```

### Web API
- Endpoint: `http://10.x.x.xxx:8080` (or configured port)
- REST API for programmatic access
- Can be called from scripts, cron jobs, or other services

**Container info:** CT100 on PVE1, Debian, 2 cores, 4GB RAM.

---

## Section 3: What You're Looking At

### Hermes Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    CT100 (10.x.x.xxx)                     │
│  ┌──────────────────────────────────────────────────┐    │
│  │              Hermes Agent Core                    │    │
│  │  ┌─────────┐  ┌──────────┐  ┌────────────────┐  │    │
│  │  │ Discord │  │   CLI    │  │   Web API      │  │    │
│  │  │  Bot    │  │ Terminal │  │   (REST)       │  │    │
│  │  └────┬────┘  └────┬─────┘  └───────┬────────┘  │    │
│  │       └────────────┼────────────────┘            │    │
│  │                    ▼                              │    │
│  │           ┌────────────────┐                      │    │
│  │           │  AI Engine     │                      │    │
│  │           │ (Tool + Memory)│                      │    │
│  │           └────────┬───────┘                      │    │
│  └────────────────────┼──────────────────────────────┘    │
│                       │                                    │
│                       ▼                                    │
│              ┌────────────────┐                            │
│              │   Ollama API   │  CT113 (10.x.x.xxx)        │
│              │ qwen2.5:7b    │  Port 11434 (localhost)     │
│              └────────────────┘                            │
└──────────────────────────────────────────────────────────┘
```

### Key Components

**1. Skills** — Pre-built workflows that give Hermes specialized abilities:
- **file_ops** — Read, write, search files
- **terminal** — Run shell commands on connected hosts
- **web_search** — Search and fetch web content
- **docker** — Manage Docker containers
- **proxmox** — Manage Proxmox VMs and containers
- **network** — Ping, DNS lookups, port checks
- **git** — Interact with Gitea repositories

**2. Memory** — Hermes remembers context:
- **Session memory** — What was said in the current conversation
- **Long-term memory** — Facts stored across sessions (Anthony's preferences, service details)
- **Ephemeral memory** — Temporary context that expires

**3. Plugins** — Extend Hermes' capabilities:
- Custom plugins can be added for homelab-specific tools
- Each plugin has its own set of tools and permissions

---

## Section 4: How to Read & Use It

### Chatting with Hermes

On Discord or CLI, you just talk normally:

```
Anthony: Hey Hermie, is the media stack running okay?
Hermie: Let me check! CT110 has 18 containers. Running a health check now...
       ✅ jellyfin - up since June 25
       ✅ sonarr - up since June 25
       ✅ radarr - up since June 25
       ✅ qbittorrent - up since June 25 (VPN connected)
       ...all 18 containers are healthy!
       📊 Resource usage: 45% CPU, 62% RAM, 1.2TB free on /media

Anthony: My Nextcloud share isn't working. Can you check?
Hermie: I'll look into it. Checking CT112...
       Web server (Apache): ✅ running
       Database (MariaDB): ✅ running
       Redis cache: ✅ running
       Disk space: 76% used — that's fine
       Let me check the Nextcloud app log for errors...
       Found it: The PHP memory limit is too low for large uploads.
       Would you like me to increase it from 128M to 256M?
```

### Asking Hermes to Do Things

Hermes can take action when asked. Here are examples:

| What you say | What Hermes does |
|-------------|-----------------|
| "Check disk space on all containers" | SSHes into each CT, runs `df -h`, reports results |
| "Restart the Plex container" | Runs `docker restart plex` |
| "What's the IP of my new CT?" | Checks Proxmox API or scans the network |
| "Update my Pi-hole blocklists" | SSHs into CT107, runs `pihole -g` |
| "Create a new user on Nextcloud" | Runs the `occ user:add` command |
| "Show me the Grafana logs" | Reads and returns Grafana's Docker logs |
| "What's new in Gitea since last week?" | Checks Gitea for new commits |

---

## Section 5: Beginner Routine

**Daily:**
1. No routine needed — Hermes is passive until you talk to it
2. If something breaks, ask Hermes to investigate before SSHing in yourself

**Weekly (use on Friday):**
1. Ask Hermes: "Give me a homelab health report"
2. Hermes will check all services, disk usage, and uptime
3. Ask: "Are there any updates available for my containers?"

**Monthly:**
1. Ask: "Clean up old Docker images and volumes"
2. Ask: "Show me which containers are using the most resources"
3. Review Hermes' long-term memory: Remove old or incorrect facts

---

## Section 6: Don't Panic Rules

- **"Hermes isn't responding on Discord!"** Check that CT100 is running. Then check the Discord bot process. Restart if needed: `systemctl restart hermes-discord-bot`.

- **"Hermes gave a wrong answer"** Correct it! Say "Actually, that's not right — here's the correct info." Hermes learns from corrections.

- **"Hermes says 'Ollama not reachable'"** The LLM server on CT113 is down. SSH into CT113 and check: `systemctl status ollama`. Restart: `systemctl restart ollama`.

- **"Hermes doesn't have permission to do something"** Some actions need elevated permissions. Check the Hermes config file for allowed tools and hosts. You may need to add SSH keys or grant sudo access.

- **"Hermes keeps forgetting something"** Long-term memory needs to be explicitly stored. Say "Remember that [fact]" to save it permanently.

- **"Hermes is running slowly"** The qwen2.5:7b model on CT113 (16GB, 4 cores) can be slow for complex tasks. Simpler questions get faster responses. Or consider upgrading the Ollama container.

- **"I accidentally told Hermes to do something dangerous"** Most destructive actions require confirmation. Hermes should ask "Are you sure?" before destructive operations. If it's too late, undo the change manually.

---

## Section 7: Quick Reference Card

| Item | Value |
|------|-------|
| **Host CT** | CT100 on PVE1 |
| **IP** | 10.x.x.xxx |
| **OS** | Debian |
| **Resources** | 2 cores, 4GB RAM |
| **Access** | Discord / CLI / Web API |
| **AI backend** | Ollama on CT113 (qwen2.5:7b) |
| **Developer** | Nous Research |
| **Nickname** | Hermie |

### Useful Commands

```bash
# SSH into CT100
ssh root@10.x.x.xxx

# Start Hermes CLI
hermes

# Check Hermes status
systemctl status hermes

# Restart Hermes
systemctl restart hermes

# View Hermes logs
journalctl -u hermes -f

# List available skills
hermes skills list

# View memory
hermes memory list

# Add a fact to long-term memory
hermes memory add "The homelab has 18 Docker containers on CT110"

# Update Hermes configuration
nano /etc/hermes/config.yaml
```

### Hermes Config File Location
```
/etc/hermes/config.yaml
```

### Key Config Options
| Setting | Purpose |
|---------|---------|
| `ollama_endpoint` | Where to find Ollama (CT113:11434) |
| `discord_token` | Discord bot token |
| `allowed_hosts` | Which containers Hermes can SSH into |
| `tools_enabled` | Which tools are available (terminal, docker, etc.) |
| `memory_enabled` | Enable/disable long-term memory |

### Important Notes
- **Hermes can be conversational** — you don't need to use special syntax
- **It respects permissions** — it won't do destructive things without confirmation
- **It can work offline** — since it uses local Ollama, no internet needed
- **Skills are extensible** — new skills can be added for homelab-specific tasks
- **Anthony calls it Hermie** — both names work

---

*Generated for Anthony's homelab.*
