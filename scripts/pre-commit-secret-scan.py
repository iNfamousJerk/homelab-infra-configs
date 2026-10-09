#!/usr/bin/env python3
"""Pre-commit hook: detect secrets before they hit the repo.

Requires Python 3.6+ (uses f-strings).

Installed per-repo at .git/hooks/pre-commit. Scans staged files for patterns
matching API keys, passwords, tokens, hashes and private keys. Rejects the
commit if any are found with real (non-placeholder) values.

Usage:
  pre-commit-secret-scan.py                 # scan staged content (hook mode)
  pre-commit-secret-scan.py FILE [FILE...]  # scan specific files on disk
  pre-commit-secret-scan.py --all           # scan every tracked file

── Why this file changed ─────────────────────────────────────────────────
The previous version reported "clean" on three files in this repo that
between them held two plaintext root passwords, four live *arr API keys and
a bcrypt hash. Three gaps let all of that through:

  1. No pattern matched a bare `PASS="..."` assignment at all. The generic
     patterns keyed on names like api_key/token/secret, and "password" was
     not among them.
  2. The hex pattern required 40+ characters. *arr keys are exactly 32.
  3. The name group `api[_-]?key|apikey|api_token|token|secret` did not
     match `RADARR_KEY`, so even a widened length would have missed it.

A fourth gap was latent: is_placeholder() tested the whole matched text, and
PLACEHOLDER_PATTERNS included `\\$[A-Z_]+`, so any finding that merely
contained something like `$HOME` anywhere was discarded. Matches now capture
the secret itself in a `secret` group and only that is placeholder-tested.
"""

import os
import re
import sys
import subprocess

# ── Patterns ──────────────────────────────────────────────
# Each entry is (description, compiled regex). Where a pattern matches
# surrounding context (a key name, quotes), it captures just the sensitive
# part as (?P<secret>...) so placeholder detection is applied to the value
# rather than to the whole line.

# Key names that imply the value is sensitive. Deliberately includes bare
# `*_key` so RADARR_KEY / SONARR_KEY style names are covered. The trailing
# \w* matters: without it `PVE_PASSWORDS` (plural) does not match, because
# the alternation stops at `pass` and leaves `WORDS` before the `=`.
_SECRET_NAME = (
    r"(?:[a-z0-9_.-]*(?:pass|passwd|password|pwd|secret|token|apikey|"
    r"api[_-]?key|auth[_-]?key|access[_-]?key|private[_-]?key|[a-z0-9]+_key)\w*)"
)

# Values short enough to be a word are usually placeholders or enum values,
# so assignments require 6+ characters to flag.
_MIN_VALUE = 6

# Ordered most specific first: several patterns can cover the same value, and
# the first match wins the label, so "GitHub PAT" beats a generic assignment.
SECRET_PATTERNS = [
    # Unix crypt / bcrypt password hashes — the OPNsense root hash was one
    # of these and sat in a file labelled "sanitized".
    ("Password hash", re.compile(
        r'(?P<secret>\$(?:2[abxy]?|1|5|6)\$[A-Za-z0-9./$]{16,})')),

    # Proxmox VE / PBS API tokens. PVE separates id and secret with '=',
    # PBS with ':'; the secret itself is a UUID.
    ("Proxmox API token", re.compile(
        r'(?P<secret>[A-Za-z0-9_.-]+@[A-Za-z0-9]+![A-Za-z0-9_-]+[=:]'
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})')),

    # Discord webhooks (real URLs, not placeholders)
    ("Discord Webhook URL", re.compile(
        r'(?P<secret>discord\.com/api/webhooks/\d{17,20}/[a-zA-Z0-9_\-]{30,})')),

    # GitHub tokens
    ("GitHub PAT", re.compile(r'(?P<secret>ghp_[a-zA-Z0-9]{36})')),
    ("GitHub OAuth", re.compile(r'(?P<secret>gho_[a-zA-Z0-9]{36})')),
    ("GitHub App Token", re.compile(r'(?P<secret>ghu_[a-zA-Z0-9]{36})')),
    ("GitHub Refresh", re.compile(r'(?P<secret>ghr_[a-zA-Z0-9]{36})')),
    ("GitHub fine-grained PAT", re.compile(r'(?P<secret>github_pat_[a-zA-Z0-9_]{60,})')),

    # Slack tokens
    ("Slack Token", re.compile(r'(?P<secret>xox[baprs]-[0-9a-zA-Z\-]{12,})')),

    # AWS
    ("AWS Access Key", re.compile(r'(?P<secret>AKIA[0-9A-Z]{16})')),
    ("AWS Secret Key", re.compile(
        r'(?i)aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*'
        r'["\'](?P<secret>[a-zA-Z0-9/+=]{40})["\']')),

    # Private keys
    ("Private Key block", re.compile(
        r'(?P<secret>-----BEGIN\s+(?:RSA|EC|DSA|OPENSSH|PGP)?\s*PRIVATE\s+KEY-----)')),

    # JWT tokens (eyJ... format)
    ("JWT Token", re.compile(
        r'(?P<secret>eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,})')),

    # Hex API keys. Floor is 32, not 40: that is the *arr key length.
    ("API key (hex)", re.compile(
        rf'(?i)\b{_SECRET_NAME}\s*[:=]\s*'
        r'["\']?(?P<secret>[a-f0-9]{32,})["\']?')),

    # Base64/alphanumeric secrets of 32+ chars.
    ("API key (base64)", re.compile(
        rf'(?i)\b{_SECRET_NAME}\s*[:=]\s*'
        r'["\']?(?P<secret>[a-zA-Z0-9+/=_-]{32,})["\']?')),

    # Any assignment to a sensitive-looking name. This is the broad net that
    # the previous version lacked entirely. Kept last so the specific
    # patterns above get to name the finding.
    ("Credential assignment", re.compile(
        rf'(?i)\b{_SECRET_NAME}\s*[:=]\s*'
        rf'["\']?(?P<secret>[^\s"\'`,;#\\]{{{_MIN_VALUE},}})["\']?')),
]

# A dict or list whose *name* implies secrets, e.g. the PVE_PASSWORDS map
# this repo shipped. Name-based matching alone cannot see these, because the
# keys are addresses and the secret is the value:
#
#     PVE_PASSWORDS = {
#         "10.0.7.64": "<the-real-password-was-here>",
#     }
#
SECRET_CONTAINER_OPEN = re.compile(rf'(?i)\b{_SECRET_NAME}\s*[:=]\s*[{{\[]')
# Inside such a container, flag values introduced by ':' or '=' only. Matching
# bare comma-separated items too would flag the "10.0.7.64" keys as secrets.
CONTAINER_VALUE = re.compile(rf'[:=]\s*["\'](?P<secret>[^"\'\s]{{{_MIN_VALUE},}})["\']')

# Applied to the captured secret only. A value is treated as safe if it is a
# recognisable stand-in: an env substitution, an angle-bracket token, an
# explicit redaction, or a CHANGE_ME style marker.
PLACEHOLDER_PATTERNS = re.compile(
    r'''
      \$\{                      # ${VAR} or ${VAR:?msg} substitution
    | ^\$[A-Za-z_][A-Za-z0-9_]*$   # a bare $VAR as the entire value
    | ^%[A-Za-z_]+%$            # %VAR% (windows style)
    | \{[A-Za-z_]\w*\}          # {token} — f-string / template interpolation
    | \[REDACTED\]
    | \bREDACTED\b
    | CHANGE_?ME
    | CHANGE[_-]?THIS           # change_this_to_a_secure_random_token
    | CHANGEIT
    | ^\*+$                     # *** as a redaction
    | <[^>]*>                   # <your-token>, <uuid> — anywhere in the value,
                                # e.g. root@pam!panel=<uuid> in a doc comment
    | ^YOUR[_-]
    | ^EXAMPLE
    | PLACEHOLDER
    | ^x{6,}$                   # xxxxxxxx
    | ^0+$
    ''',
    re.IGNORECASE | re.VERBOSE
)

# Files to skip (binary, vendor, etc.)
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2',
                   '.ttf', '.eot', '.pdf', '.zip', '.tar', '.gz', '.bz2', '.xz',
                   '.pyc', '.o', '.so', '.dll', '.exe'}
# Matched per path component, so a nested app/node_modules/ is skipped too —
# the previous startswith() check only caught these at the repo root.
SKIP_DIRS = {'node_modules', 'vendor', '__pycache__', '.git', 'dist', 'build'}


# Values that a secret-named setting legitimately holds without being a
# secret — a key file path, a CA bundle, an enum. Kept narrow on purpose:
# a broad "contains a slash" rule would suppress base64 secrets, e.g. the
# AWS example key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY.
NOT_SECRET_PATTERNS = re.compile(
    r'''
      ^~?/                          # /etc/... or ~/.ssh/...
    | ^\.{1,2}/                     # ./ or ../
    | ^[a-z][a-z0-9+.-]*://         # scheme://...
    | ^[A-Za-z_][A-Za-z0-9_.]*\(    # re.compile(... — a call, not a literal
    | ^(?:true|false|on|off|yes|no|none|null|auto|latest|
         unless-stopped|accept-new|openvpn|wireguard)$
    ''',
    re.IGNORECASE | re.VERBOSE
)


def is_placeholder(value):
    """True if a matched value is a recognisable stand-in rather than a secret."""
    return bool(PLACEHOLDER_PATTERNS.search(value))


def is_not_secret(value):
    """True if the value is a path/URL/enum rather than a credential."""
    return bool(NOT_SECRET_PATTERNS.search(value))


def should_skip(filepath):
    if os.path.splitext(filepath)[1].lower() in SKIP_EXTENSIONS:
        return True
    return any(part in SKIP_DIRS for part in filepath.replace('\\', '/').split('/'))


def _container_extent(content, open_idx):
    """Return the slice of `content` from an opening brace to its match.

    Falls back to end-of-text if the container is never closed, which is fine
    for scanning purposes.
    """
    pairs = {'{': '}', '[': ']'}
    opener = content[open_idx]
    closer = pairs[opener]
    depth = 0
    for i in range(open_idx, len(content)):
        if content[i] == opener:
            depth += 1
        elif content[i] == closer:
            depth -= 1
            if depth == 0:
                return content[open_idx:i + 1], open_idx
    return content[open_idx:], open_idx


def scan_text(filepath, content):
    """Return [(filepath, line, description, secret)] for one file's content."""
    findings = []
    seen = set()

    def record(desc, value, abs_pos):
        if is_placeholder(value) or is_not_secret(value):
            return
        line_num = content.count('\n', 0, abs_pos) + 1
        # Several patterns can cover the same value; report it once, with the
        # label of the first (most specific) pattern that matched.
        key = (line_num, value)
        if key in seen:
            return
        seen.add(key)
        findings.append((filepath, line_num, desc, value))

    for desc, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(content):
            value = match.groupdict().get('secret') or match.group()
            record(desc, value, match.start())

    for opener in SECRET_CONTAINER_OPEN.finditer(content):
        block, base = _container_extent(content, opener.end() - 1)
        for match in CONTAINER_VALUE.finditer(block):
            record("Credential in secret-named collection",
                   match.group('secret'), base + match.start('secret'))

    findings.sort(key=lambda f: (f[1], f[3]))
    return findings


def _git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True)


def scan_staged_files():
    """Scan staged content — the hook path. Reads from the index, not the
    working tree, so a file staged then edited is checked as it will land."""
    result = _git('diff', '--cached', '--name-only', '--diff-filter=ACM')
    staged = [f for f in result.stdout.strip().split('\n') if f.strip()]

    findings = []
    for filepath in staged:
        if should_skip(filepath):
            continue
        blob = _git('show', f':{filepath}')
        if blob.returncode != 0:
            continue
        findings.extend(scan_text(filepath, blob.stdout))
    return findings


def scan_paths(paths):
    """Scan files on disk — used by --all and by the test suite."""
    findings = []
    for filepath in paths:
        if should_skip(filepath) or not os.path.isfile(filepath):
            continue
        try:
            with open(filepath, encoding='utf-8', errors='replace') as fh:
                content = fh.read()
        except OSError:
            continue
        findings.extend(scan_text(filepath, content))
    return findings


def redact(value):
    if len(value) > 22:
        return value[:15] + '***' + value[-4:]
    if len(value) > 8:
        return value[:4] + '***'
    return '***'


def main():
    argv = sys.argv[1:]
    if argv == ['--all']:
        tracked = _git('ls-files').stdout.strip().split('\n')
        findings = scan_paths([f for f in tracked if f.strip()])
    elif argv:
        findings = scan_paths(argv)
    else:
        findings = scan_staged_files()

    if not findings:
        print("✅  Secret scan: clean")
        return 0

    print("\n❌  SECRETS DETECTED — COMMIT BLOCKED\n")
    for filepath, line, desc, value in findings:
        print(f"  📁 {filepath}:{line}")
        print(f"     🔴 {desc}: {redact(value)}")
    print(f"\n  ⚠️  {len(findings)} potential secret(s) found.")
    print("  → Remove them from staged files or replace with placeholders.")
    print("  → Use '${VAR_NAME}', '[REDACTED]', or '<VAR_NAME>' notation.")
    print("  → To override: git commit --no-verify\n")
    return 1


if __name__ == '__main__':
    sys.exit(main())
