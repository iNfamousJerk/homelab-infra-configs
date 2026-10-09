#!/bin/bash
# deploy-stack.sh <repo-name> [target-dir]
# One-command deploy of a Gitea stack repo — pairs with gitify-stack.sh.
#
# Examples:
#   ./deploy-stack.sh stack-pirate /opt/pirate-stack
#   ./deploy-stack.sh stack-librarr              # defaults to /opt/librarr
#   DRY_RUN=1 ./deploy-stack.sh stack-keycloak   # clone/pull only, no compose start
#
# Flow: clone-or-pull -> .env from .env.example -> warn on PBS-restored dirs ->
#       docker compose pull -> up -d -> ps
#
# No secrets in this file. Export GITEA_BASE with credentials before running:
#   export GITEA_BASE="http://InfamousJerk:PASSWORD@10.0.30.106:3002"
set -euo pipefail

REPO="${1:?usage: deploy-stack.sh <repo-name> [target-dir]}"
TARGET="${2:-/opt/${REPO#stack-}}"
BASE="${GITEA_BASE:-http://gitea.lan:3002}"
REMOTE="${BASE}/InfamousJerk/${REPO}.git"

# 1. Get the code (clone fresh or pull existing)
if [ -d "$TARGET/.git" ]; then
  REMOTE_NAME="$(git -C "$TARGET" remote | head -1)"
  echo "==> Pulling latest $REPO into $TARGET (remote: $REMOTE_NAME)"
  git -C "$TARGET" pull -q "$REMOTE_NAME" main
else
  echo "==> Cloning $REPO -> $TARGET"
  mkdir -p "$(dirname "$TARGET")"
  git clone -q "$REMOTE" "$TARGET"
  git -C "$TARGET" config user.name "hermes"
  git -C "$TARGET" config user.email "hermes@homelab.local"
  git -C "$TARGET" config --global --add safe.directory "$TARGET" 2>/dev/null || true
fi

cd "$TARGET"

# 2. Secrets file
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "!! Created .env from .env.example - EDIT the CHANGE_ME values before starting!"
fi

# 3. Runtime data dirs excluded from git — remind about PBS restore
for d in $(grep -E '^[A-Za-z0-9_/.-]+/?$' .gitignore 2>/dev/null | grep -vE '^\*|^!|^\.env' | head -5); do
  [ -d "$d" ] || echo "!! $d/ is missing - restore it from PBS before/after first start if this stack needs it"
done

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "==> DRY RUN - not starting compose (DRY_RUN=1)"
  exit 0
fi

# 4. Go
docker compose pull -q 2>/dev/null || true
docker compose up -d
sleep 3
docker compose ps
