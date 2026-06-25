#!/bin/bash
set -e

# sync-public.sh — Mergea main → public, excluye datos sensibles, pushea a origin
# Uso: ./sync-public.sh ["mensaje opcional"]

BRANCH_CURRENT=$(git rev-parse --abbrev-ref HEAD)
MSG="${1:-chore: sync main -> public}"

echo "=== 1. Push main a private ==="
git push private main

echo "=== 2. Checkout public (force) ==="
git checkout public --force

echo "=== 3. Merge main --no-commit ==="
git merge main --no-commit

echo "=== 4. Excluir datos sensibles ==="
git rm --cached session_history.json session_history.db 2>/dev/null || true
git rm --cached db_backups/session_history_*.db 2>/dev/null || true

echo "=== 5. Commit merge ==="
git commit --no-edit -m "$MSG"

echo "=== 6. Push a origin/public ==="
git push origin public

echo "=== 7. Force-push a origin/main (sanitizado) ==="
git push origin public:main --force

echo "=== 8. Volver a $BRANCH_CURRENT ==="
git checkout "$BRANCH_CURRENT"

echo "=== OK ==="
