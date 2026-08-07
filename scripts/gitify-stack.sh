#!/bin/bash
# gitify-stack.sh <stack-dir> <repo-name> [extra-gitignore...]
# Versions a live docker-compose stack dir as a git repo and pushes to Gitea.
# The result: every stack is one `git clone` away from a clean rebuild.
#
# Usage examples:
#   ./gitify-stack.sh /opt/pirate-stack stack-pirate config/
#   ./gitify-stack.sh /opt/librarr stack-librarr data/
#
# Conventions applied automatically:
#   - .env ignored (secrets stay off git); .env.example committed with CHANGE_ME
#   - *.bak, *.pem, *.key, *.log, data/ ignored
#   - git identity set to hermes@homelab.local (per-repo)
#
# Credentials: no secrets embedded in this file. Either:
#   export GITEA_BASE="http://USER:PASS@10.2.7.x:3002"
# or let git use its stored credential helper. The gitea remote is added as
# $GITEA_BASE/InfamousJerk/<repo>.git
set -euo pipefail

DIR="$1"; REPO="$2"; shift 2
BASE="${GITEA_BASE:-http://10.2.7.x:3002}"
REMOTE="${BASE}/InfamousJerk/${REPO}.git"

cd "$DIR"
[ -d .git ] && { echo "SKIP $DIR (already a git repo)"; exit 0; }

# git's safe.directory guard: repo dir owned by non-root (e.g. container uid)
git config --global --add safe.directory "$DIR" 2>/dev/null || true
git init -b main >/dev/null
git config user.name "hermes"
git config user.email "hermes@homelab.local"

{
  echo ".env"
  echo "*.env"
  echo "!*.env.example"
  echo "*.bak"
  echo "*.pem"
  echo "*.key"
  echo "*.log"
  echo "data/"
  for x in "$@"; do echo "$x"; done
} > .gitignore

if [ -f .env ] && [ ! -f .env.example ] && [ ! -f env.example ]; then
  sed -E 's/=.*/=CHANGE_ME/' .env > .env.example
  echo "  (generated .env.example from .env)"
fi

git add -A
git commit -q -m "feat: version ${REPO} live compose stack (rebuild reference)"
git remote add gitea "$REMOTE"
git push -qu gitea main
echo "DONE $DIR -> $REPO ($(git rev-parse --short HEAD))"
