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

echo "=== 3. Aplicar main sin heredar historial privado ==="
# Un squash evita que commits privados (que incluyen la base y backups) queden
# como ancestros de public, incluso si los archivos se eliminan antes del
# commit público.
git merge --squash main || true

echo "=== 4. Excluir datos sensibles ==="
git rm -f session_history.json session_history.db session_history_legacy_freeze.json 2>/dev/null || true
git rm -f codex_sub_costs.json 2>/dev/null || true
git rm -f db_backups/session_history_*.db 2>/dev/null || true

if git diff --name-only --diff-filter=U | grep -q .; then
  echo "ERROR: quedan conflictos no resueltos después de excluir datos sensibles"
  git diff --name-only --diff-filter=U
  exit 1
fi

echo "=== 5. Commit merge ==="
git commit --no-edit -m "$MSG"

echo "=== 6. Push a origin/public ==="
git push origin public

echo "=== 7. Force-push a origin/main (sanitizado) ==="
git push origin public:main --force

echo "=== 8. Volver a $BRANCH_CURRENT ==="
git checkout "$BRANCH_CURRENT"

echo "=== OK ==="
