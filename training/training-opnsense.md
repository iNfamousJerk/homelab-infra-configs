# OPNsense Beginner's Manual — <username>'s Homelab
*Tailored to your actual setup.*

---

## 1. What OPNsense Actually Is (the mental model)

**Think of OPNsense as the air traffic control tower for your home network.**

Every packet of data flying in or out of your house has to get permission. OPNsense sits at the front gate and decides:
- Who gets in (firewall rules — like a bouncer checking IDs)
- Who gets out (outbound rules — like making sure nobody leaves through a fire exit)
- Where everyone sits (DHCP — handing out IP addresses like seat assignments)
- What's the fastest route (routing — the actual "traffic control")

**The Zimaboard factor:** Your OPNsense runs on a **Zimaboard** — a tiny, fanless, low-power computer that's basically a thin client on steroids. It's not a beefy server; it's a purpose-built appliance that just does one job: routing and firewalling. And it does that job beautifully with hardly any power draw.

**Two IPs, one purpose:**
- **10.x.x.xxx** — The main interface (your homelab VLAN/subnet)
- **192.168.x.x/24** — A secondary LAN interface (maybe your house network or another VLAN)

---

## 2. Getting In

- **URL:** https://10.x.x.xxx
- **Login:** There is no stored password in this documentation. If you don't know the password:
  - Default OPNsense credentials (if never changed): `root` / `<password>`
  - Or check your password manager
  - Or physically plug into the Zimaboard and reset via serial console

**Note:** Like everything else in this lab, the HTTPS cert is self-signed. Click through.

---

## 3. What You're Looking At

### The Dashboard
The first thing you see after logging in — it's like the cockpit of a plane:

- **Traffic Graph** — Live bandwidth usage. Wavy lines going up and down. Normal.
- **Firewall Log** — Shows blocked/rejected packets scrolling in real time. Don't freak out — a lot of blocked traffic is just internet background noise (bots poking at your IP from overseas).
- **System Information** — CPU, RAM, disk, uptime. On the Zimaboard, everything should be cool and quiet. If CPU is pegged at 100%, you've got a problem.
- **Gateways** — Shows your WAN (internet) connection status. Green = online. Red = your internet is down.

### The Menu Bar (Left Side)
- **System** — Settings, updates, users, firmware
- **Interfaces** — Your network ports (WAN, LAN, OPT ports)
- **Firewall** — Rules, NAT, traffic shaping — the big one you'll spend time in
- **Services** — DHCP, DNS forwarder, Unbound, etc.
- **VPN** — OpenVPN, IPsec, WireGuard
- **Diagnostics** — Ping, traceroute, packet capture, logs

---

## 4. How to Read the Key Stuff

### Firewall Rules
Think of these as "permission slips." Each rule says: "Traffic from A going to B on port C is ALLOWED or BLOCKED."

- **Top to bottom order matters!** OPNsense checks rules in order. The first match wins. So put your most specific rule at the top, your broad "block everything" rule at the bottom.
- **Green arrow** = allow. **Red X** = block.
- **Log column** — If checked, every packet matching this rule gets logged. Use sparingly or you'll drown in log data.

### DHCP (IP Address Leases)
OPNsense is your DHCP server (handing out IPs). The DHCP leases page shows:
- **IP Address** — Who got what
- **Hostname** — The device name (if it told us)
- **MAC Address** — The physical hardware address of the device
- **Lease Start / End** — How long the address is reserved
- **Status** — Active (connected), Expired (was here, left), Offline

### DNS Forwarding to Pi-hole
OPNsense is configured to forward all DNS requests to **Pi-hole** at 10.x.x.xxx. This means:
1. Your devices ask OPNsense for DNS
2. OPNsense says "I don't know, let me ask Pi-hole"
3. Pi-hole checks its blocklist and either returns the real IP or blocks it if it's an ad/tracker
4. Pi-hole asks **Unbound** (its own recursive resolver on port 5335) if the answer isn't cached

### Port Mirror to Zeek
OPNsense sends a copy of ALL traffic to **Zeek** (CT101 on PVE2) for security monitoring. This is done via port mirroring — Zeek sees everything but can't interfere. Think of it as a security camera watching the lobby.

---

## 5. A Beginner Routine

**Daily (20 seconds):**
1. Check that you can reach the internet. Can you browse to google.com? If yes, OPNsense is doing its job.

**Weekly (2 minutes):**
1. Log into OPNsense at https://10.x.x.xxx
2. Check the Dashboard — any red/gateway alerts? If the WAN gateway is red, your ISP is having issues.
3. Check the Firewall Log for 5 seconds. If you see a LOT of traffic from the same IP hitting the same port, that's a port scan — OPNsense is blocking it, which is correct.

**Monthly (10 minutes):**
1. System → Firmware → Check for updates. OPNsense gets security patches regularly.
2. After updating, reboot if prompted (schedule for 3 AM or whenever nobody's using the network).
3. Review DHCP leases — any unknown devices? Maybe kick them off.
4. Review Aliases (Firewall → Aliases) — keep your IP lists current.

---

## 6. Don't Panic Rules

- **"I locked myself out of OPNsense!"** The web UI is at 10.x.x.xxx. If you changed the port or disabled HTTPS, physically connect to the Zimaboard with a monitor and keyboard, or use the serial console to reset the config.
- **"The firewall log is FULL of blocked traffic!"** That's normal. The internet is constantly being scanned by bots and researchers. OPNsense blocks it all. You should only worry if you see ALLOWED traffic you didn't authorize.
- **"My internet is slow!"** Log into OPNsense, go to Dashboard → Traffic Graph. Is your uplink saturated? Someone might be downloading a huge file or streaming 4K. Check the top talkers under Reports → Traffic.
- **"I can't reach a certain website!"** Could be Pi-hole blocking it. Try pausing Pi-hole and see if that's the culprit (http://10.x.x.xxx/admin → Disable Blocking).
- **"OPNsense itself feels slow"** The Zimaboard is not a powerhouse. If you add too many rules or services, it'll bog down. Keep it lean.
- **"The Zimaboard is hot to the touch!"** It's fanless and passively cooled. Warm is normal. Scorching hot is not — make sure it has airflow.

---

## 7. Quick Reference Card

| I want to... | Do this... |
|-------------|-----------|
| Check if my internet is up | Dashboard → look at WAN gateway (green = good) |
| See who's using my network | Services → DHCPv4 → Leases |
| Add a firewall rule | Firewall → Rules → [Interface] → Add |
| Block a specific device | Firewall → Rules → [Interface] → Add "Block" rule with its IP |
| Update OPNsense | System → Firmware → Check for updates |
| Restart the firewall | System → Power → Reboot |
| See what Zeek is monitoring | You can't from here — check Zeek on PVE2 CT101 |
| Pause ad-blocking temporarily | Log into Pi-hole at http://10.x.x.xxx/admin → Disable |
| Check VPN status | VPN → [Your VPN type] → Status |

---

*Generated for <username>'s homelab.*
