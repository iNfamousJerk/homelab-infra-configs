#!/usr/bin/env python3
"""Pre-commit hook: detect secrets before they hit the repo.

Installed per-repo at .git/hooks/pre-commit.
Scans staged files for patterns matching API keys, passwords, tokens, and
private keys. Rejects the commit if any are found with real (non-placeholder)
values.

Usage:
  Can be run standalone: python3 .git/hooks/pre-commit
  Or symlinked: ln -sf ../../scripts/pre-commit-secret-scan.py .git/hooks/pre-commit
"""

import os
import re
import sys
import subprocess

# ── Patterns ──────────────────────────────────────────────
# First group  = description for the warning
# Second group = compiled regex
SECRET_PATTERNS = [
    # Discord webhooks (real URLs, not placeholders)
    ("Discord Webhook URL", re.compile(
        r'discord\.com/api/webhooks/\d{17,20}/[a-zA-Z0-9_\-]{30,}')),
    
    # GitHub tokens
    ("GitHub PAT", re.compile(r'ghp_[a-zA-Z0-9]{36}')),
    ("GitHub OAuth", re.compile(r'gho_[a-zA-Z0-9]{36}')),
    ("GitHub App Token", re.compile(r'ghu_[a-zA-Z0-9]{36}')),
    ("GitHub Refresh", re.compile(r'ghr_[a-zA-Z0-9]{36}')),
    
    # Slack tokens
    ("Slack Bot Token", re.compile(r'xoxb-[0-9a-zA-Z\-]{24,}')),
    
    # AWS
    ("AWS Access Key", re.compile(r'AKIA[0-9A-Z]{16}')),
    ("AWS Secret Key", re.compile(r'(?i)aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9/+=]{40}["\']')),
    
    # Private keys
    ("RSA Private Key", re.compile(r'-----BEGIN\s+(RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY-----')),
    
    # Generic high-entropy tokens (base64, hex, alphanumeric 32+ chars)
    # Skip if they contain obvious placeholder patterns
    ("Generic API Key (40+ char hex)", re.compile(
        r'(?i)(api[_-]?key|apikey|api_token|token|secret|password)["\']?\s*[:=]\s*["\'][a-f0-9]{40,}["\']')),
    ("Generic API Key (32+ char base64)", re.compile(
        r'(?i)(api[_-]?key|apikey|api_token|token|secret)["\']?\s*[:=]\s*["\'][a-zA-Z0-9+/=]{32,}["\']')),

    # JWT tokens (eyJ... format)
    ("JWT Token", re.compile(r'eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}')),
]

PLACEHOLDER_PATTERNS = re.compile(
    r'YOUR_WEBHOOK_URL|<DISCORD_WEBHOOK_URL>|\[REDACTED\]|\*\*\*|<your-|<strong-|<new_|<pbs-user|<admin-|<db-|<target-|<your_password|CHANGE_ME|__PLACEHOLDER__|\$\{|\$[A-Z_]+|CHANGEME',
    re.IGNORECASE
)

# Files to skip (binary, vendor, etc.)
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2',
                   '.ttf', '.eot', '.pdf', '.zip', '.tar', '.gz', '.bz2', '.xz',
                   '.pyc', '.o', '.so', '.dll', '.exe'}
SKIP_PATHS = {'node_modules/', 'vendor/', '__pycache__/', '.git/'}


def is_placeholder(value):
    """Check if a matched value is actually a sanitized placeholder."""
    return bool(PLACEHOLDER_PATTERNS.search(value))


def scan_staged_files():
    """Scan all staged files for secret patterns."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True, text=True
    )
    staged_files = [f for f in result.stdout.strip().split('\n') if f.strip()]
    
    findings = []
    for filepath in staged_files:
        # Skip binary/vendor files
        ext = os.path.splitext(filepath)[1].lower()
        if ext in SKIP_EXTENSIONS:
            continue
        if any(filepath.startswith(p) for p in SKIP_PATHS):
            continue
        
        # Get the staged content
        result = subprocess.run(
            ['git', 'show', f':{filepath}'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            continue
        
        content = result.stdout
        
        for desc, pattern in SECRET_PATTERNS:
            for match in re.finditer(pattern, content):
                value = match.group()
                # Skip placeholders
                if is_placeholder(value):
                    continue
                # Get line number
                line_num = content[:match.start()].count('\n') + 1
                findings.append((filepath, line_num, desc, value[:40]))
    
    return findings


def main():
    python_version = sys.version_info
    if python_version < (3, 6):
        print("WARNING: pre-commit secret scan requires Python 3.6+")
        sys.exit(0)
    
    findings = scan_staged_files()
    
    if findings:
        print("\n❌  SECRETS DETECTED IN STAGED FILES — COMMIT BLOCKED\n")
        for filepath, line, desc, value in findings:
            redacted = value[:15] + '***' + value[-4:] if len(value) > 22 else value
            print(f"  📁 {filepath}:{line}")
            print(f"     🔴 {desc}: {redacted}")
        print(f"\n  ⚠️  {len(findings)} potential secret(s) found.")
        print("  → Remove them from staged files or replace with placeholders.")
        print("  → Use '${VAR_NAME}', '[REDACTED]', or '<VAR_NAME>' notation.")
        print("  → To override: git commit --no-verify\n")
        sys.exit(1)
    else:
        print("✅  Secret scan: clean")
        sys.exit(0)


if __name__ == '__main__':
    main()
