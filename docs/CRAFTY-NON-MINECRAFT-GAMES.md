# Running Non-Minecraft Games in Crafty (CS2 + friends)

Crafty Controller's native **SteamCMD** server type is a trap for CS2 and most
non-Minecraft games: it wants Crafty's own SteamCMD to log in with an account
(anonymous no longer works for CS2), it re-downloads the game, and the binary
path/environment never lines up. Verified working alternative below — tested
with Counter-Strike 2 (AppID 730) hosted alongside a Minecraft server on one
Crafty instance.

## The core trick: Crafty's hidden generic launcher

Crafty's `start_server` dispatches on the DB `type` column with a match
(`app/classes/shared/server.py`):

```python
match HelperServers.get_server_type_by_id(self.server_id):
    case "minecraft-java" | "hytale":
        self.do_generic_start(user_id, user_lang)   # <-- plain command runner
    case "minecraft-bedrock":
        self.do_minecraft_bedrock_start(user_id, user_lang)
    case "steam_cmd":
        self.do_steam_server_start(user_id, user_lang)
```

There is **no `generic` case**. Setting `type="generic"` makes Crafty fall
through the match without ever spawning a process, so `self.process` stays
`None` and Start dies with:

```
AttributeError: 'NoneType' object has no attribute 'poll'
```

Fix: use `type="minecraft-java"`. `do_generic_start` is a plain
`subprocess.Popen(server_command, cwd=server_path)` — it runs *anything*,
Java not required. The type name is just a label Crafty dispatches on.

## Recipe (works for any game server)

### 1. Get the game files

Download the server with SteamCMD yourself (the account this runs under needs
the game licence, see note below):

```bash
mkdir -p /opt/steamcmd && cd /opt/steamcmd
curl -sL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz | tar xz
./steamcmd.sh +force_install_dir /opt/<game> +login <user> +app_update <APPID> validate +quit
```

- `force_install_dir` MUST come before `login` on the command line, or you get
  the message `Please use force_install_dir before logon!`.
- Free-to-play games (CS2) reject anonymous installs with
  `App '<APPID>' state is 0x202`. Fix: log in with a real account and add
  `+app_license_request <APPID>` once to activate the free licence. Log it
  said `AppID <APPID> already owned` afterwards.
- `0x202` can also mean *disk*: CS2 preallocates ~61 GB and fails instantly
  with `Failed to preallocate (Not enough disk space)` once the volume fills.
  Grow the CT/VM disk first — check `du` expectations before downloading.
- Watch for the `linux32`/`linux64` SteamCMD wrapper and install 32-bit libs:
  `dpkg --add-architecture i386 && apt install lib32gcc-s1 lib32stdc++6`.

### 2. Hand files to the crafty user

```bash
chown -R crafty:crafty /opt/<game>
```

### 3. Steamworks SDK for the crafty user

The game server needs `steamclient.so` under the running user's home or it
dies with `Failed to load module '(null)/.steam/sdk64/steamclient.so`
(that `(null)` = `$HOME` unset/unknown — the giveaway). Symlink it:

```bash
mkdir -p /home/crafty/.steam/sdk64
ln -sf /opt/steamcmd/linux64/steamclient.so /home/crafty/.steam/sdk64/steamclient.so
chown -R crafty:crafty /home/crafty/.steam
```

### 4. Launcher wrapper script

Do not point Crafty at the raw binary — the game usually needs an
environment (for CS2: `LD_LIBRARY_PATH`, set by Valve's `cs2.sh`; the binary
alone crashes with `libv8.so: cannot open shared object file`).

```bash
# /opt/<game>/run-<game>.sh
#!/bin/bash
export HOME=/home/crafty          # crafty's home, not root's
cd /opt/<game>/game               # the real game root if nested
exec ./<game>.sh "$@"             # use the game's own launcher script
```

```bash
chmod +x /opt/<game>/run-<game>.sh
chown crafty:crafty /opt/<game>/run-<game>.sh
```

### 5. Register the server in Crafty

**DB route** (repeatable, matches what the UI produces) — the Crafty SQLite
DB lives at `/opt/crafty/app/config/db/crafty.sqlite`, table `servers`:

| Field             | Value                                      |
|-------------------|--------------------------------------------|
| server_name       | Piper CS2                                  |
| path              | /opt/<game>                                |
| executable        | run-<game>.sh                              |
| execution_command | ./run-<game>.sh -dedicated -port 27015 +map de_dust2 +maxplayers 12 ... |
| type              | **minecraft-java** (the generic launcher!) |
| server_ip         | 0.0.0.0                                    |
| server_port       | <game port>                                |
| auto_start        | 0                                          |
| crash_detection   | 0                                          |

The server runs with `cwd = path`, so keep the executable reference relative
(`./run-<game>.sh`). After inserting, `mkdir -p /opt/crafty/servers/<server_id>/logs`
and `chown -R crafty:crafty` it, then restart Crafty so the in-memory server
list reloads:

```bash
systemctl restart crafty
# expect: Loaded Server: ID <id> | Name: Piper CS2
```

**UI route** is fine too — the important part is the launch command and that
the server type dispatches to the generic launcher.

### 6. Public listing: Game Server Login Token (GSLT)

LAN-only works without it. For the public server list / internet players,
generate a free GSLT at `steamcommunity.com/dev/managegameservers` (AppID of
the game) and add it to the game config — CS2:

```
sv_setsteamaccount <GSLT>
```

in `game/csgo/cfg/server.cfg`. On start the log confirms with
`Gameserver logged on to Steam, assigned identity steamid:<id>`.

## Gotchas (all hit in production)

- **Crafty restart orphans running servers.** `systemctl restart crafty` does
  not stop servers cleanly; the child processes get reparented to init and
  keep their ports. New starts then die instantly on the port conflict — looks like "the server keeps
failing." Fix: stop the server **in the Crafty UI** before restarting Crafty,
and if a stray is squatting the port: `pkill -9 -f <game-binary>` then Start
again.
- **Never set `type="generic"`** — crashes the start dispatcher (see above).
- **`0x202` is a red herring** — check space first, licence second, never
  assume SteamCMD is broken.
- **Pre-existing installs are fine** — point `path` at the install dir; a
  generic server never re-downloads. Only Crafty's SteamCMD type would.
- **console port**: add `-usercon` (RCON) only if you need it — friends don't.
- Keep game + Minecraft heaps within CT RAM; CS2 wants ~3-4 GB, Paper MC
  ~2 GB — budget before both run at once.
