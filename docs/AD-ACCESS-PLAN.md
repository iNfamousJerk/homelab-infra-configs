# AD Access Management Plan — Piper Labs

Manage user access to services via Active Directory (dc-win, VM105 on PVE3).
Covers: Windows SSO (Kerberos), RDP access to VMs, domain-joined PCs,
web-service authentication (LDAP), and optional unified web SSO (Keycloak).

## 1. Core concept

AD is the **identity + policy layer**, not a service host:

- **Authenticates** — who you are (domain account, Kerberos).
- **Authorizes** — what you can reach (security group membership).
- **Configures** — what machines can do (Group Policy, GPO).

Services (Jellyfin, Nextcloud, Immich, ...) keep running on their own
CTs/VMs. AD decides *who* gets in; each service must be configured to
trust AD (LDAP or OIDC integration).

## 2. SSO decision — do we re-deploy Keycloak?

| Need | Solution | Keycloak? |
|------|----------|-----------|
| Windows / RDP / domain-joined PCs | AD native **Kerberos** SSO | No |
| File shares, mapped drives, domain resources | AD native | No |
| Web apps (Jellyfin, Nextcloud, Immich) | Per-app **LDAP** bind to AD | No (works now) |
| One login across ALL web apps | **Keycloak** federated to AD (LDAP user federation) + OIDC to apps | Yes |

- **AD alone** = Windows SSO + directory. Enough for RDP + domain PCs.
- **Keycloak (if re-deployed)** = web-SSO front door that reads users/groups
  from AD. AD stays the source of truth; Keycloak provides OIDC/SAML to
  web apps. Re-deploy only when unified web login is wanted.

## 3. Directory structure

```
piper.lan (domain)
├── Users
│   ├── Staff          (admin/ops accounts)
│   ├── Family         (Britany, Justin, guests)
│   └── Kiosk          (locked-down user accounts for mini PCs)
├── Computers
│   ├── Workstations   (user-managed PCs: gaming PC, laptop)
│   └── Kiosk-PCs     (mini PCs — locked down by GPO)
└── Groups (security groups drive service access)
    ├── g-ADMIN        (domain admins / IT)
    ├── g-Jellyfin     (can log into Jellyfin)
    ├── g-Nextcloud    (can log into Nextcloud)
    ├── g-Immich       (can log into Immich)
    ├── g-RDP-Office   (can RDP into the Office/Work VM)
    └── g-Kiosk        (kiosk PC users)
```

Rule: **assign permissions to groups, put users in groups**. Never assign
directly to individual users.

## 4. Phase 1 — Windows SSO + RDP (no Keycloak)

### RDP to a specific VM
1. On the target VM (e.g., Office CT/VM with Remote Desktop enabled):
   add `g-RDP-Office` to the **Remote Desktop Users** local group.
2. A user in `g-RDP-Office` can RDP in.
3. From a **domain-joined** PC this is **Kerberos SSO** — no second
   password prompt.

### Connect a separate PC to the server
1. Join the mini PC to the domain: `Settings > Accounts > Access work
   or school` (or `Add-Computer`), credentials = domain admin.
2. Move the PC object into `Computers/Kiosk-PCs`.
3. Apply a **GPO** to that OU, e.g.:
   - Kiosk-mode shell (only approved apps), or standard shell locked down.
   - Block USB storage, disable installation.
   - Enforce proxy (internet via designated proxy only).
   - Pin/map approved service URLs (Jellyfin, Nextcloud).
4. The user logs in with their `Kiosk` OU account; the machine is
   locked down by policy regardless of who sits at it.

## 5. Phase 2 — Web services via LDAP (AD only)

| Service | Integration | Access control |
|---------|-------------|----------------|
| Jellyfin | LDAP auth plugin (jellyfin-ldap-auth) | Group mapping (e.g., `g-Jellyfin`) |
| Nextcloud | LDAP app (`ldap` app, built in) | Group mapping to `g-Nextcloud` |
| Immich | OIDC (needs an IdP) or LDAP where supported | Group claim mapping |

- Bind Nextcloud/Jellyfin to the AD host (dc-win, port 389/636).
- Base DN = `dc=piper,dc=lan`; filter on group membership.
- Users then log into those apps with their **domain credentials**.

## 6. Phase 3 — Unified web SSO (re-deploy Keycloak)

Only when one-login-everywhere is wanted:

1. Deploy Keycloak (docker, SERVICES VLAN).
2. **LDAP user federation** to AD — Keycloak imports users/groups
   from AD; AD remains authoritative.
3. Configure **OIDC clients** in Keycloak for Jellyfin, Nextcloud,
   Immich (reuse the old `guests` realm pattern / K0lin fork notes).
4. Users log in once at Keycloak; apps redirect there.

## 7. Phase 4 — Network enforcement (OPNsense)

AD/GPO controls the *machine*; the *firewall* controls the network:

- **Family** VLAN/group → MEDIA only (Jellyfin, arrs, Immich).
- **Staff** group → SERVICES + MEDIA.
- **Kiosk** subnet → internet (via proxy) + whitelisted service IPs only.
- Content filtering = OPNsense rules / proxy, not AD.

## 8. Recommended lab order

1. Build domain + OUs + groups on dc-win.
2. Join one test PC; drop in `Computers/Kiosk-PCs`; apply a basic GPO.
3. RDP to dc-win from the domain-joined PC (Kerberos SSO).
4. Enable **Jellyfin LDAP** (easiest first integration).
5. (Optional) Re-deploy Keycloak on top of AD for unified web SSO.

## 9. Notes / gotchas

- Kerberos SSO only works for domain-joined machines; random devices
  (phones) hit LDAP/OIDC instead.
- GPO does **not** filter web content — do that at OPNsense.
- Office licensing: user-based (M365) vs machine-based (retail) matters
  for the Office VM plan.
- Kiosk "allowed internet" is best done as: GPO-enforced proxy + OPNsense
  allowlist for that subnet.
