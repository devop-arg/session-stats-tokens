#!/bin/bash
set -e

# sync-public.sh — Mergea main → public, excluye datos sensibles, pushea a origin
# Uso: ./sync-public.sh ["mensaje opcional"]

BRANCH_CURRENT=$(git rev-parse --abbrev-ref HEAD)
MSG="${1:-chore: sync main -> public}"

CODEX_SUB_COSTS_FILE="codex_sub_costs.json"
CODEX_SUB_COSTS_BACKUP=""
CODEX_SUB_COSTS_EXISTS=0

# NOTA PROVISORIA: sync-public necesita sacar este archivo del branch publico.
# Como esta ignorado y no trackeado en main, lo respaldamos/restauramos localmente.
# Queda asi por ahora, hasta definir un manejo mejor para datos privados locales.
restore_codex_sub_costs() {
  if [[ "$CODEX_SUB_COSTS_EXISTS" -eq 1 && -n "$CODEX_SUB_COSTS_BACKUP" && -f "$CODEX_SUB_COSTS_BACKUP" ]]; then
    cp -p "$CODEX_SUB_COSTS_BACKUP" "$CODEX_SUB_COSTS_FILE"
    echo "=== Restaurado $CODEX_SUB_COSTS_FILE local ==="
  fi
  if [[ -n "$CODEX_SUB_COSTS_BACKUP" ]]; then
    rm -f "$CODEX_SUB_COSTS_BACKUP"
  fi
}
trap restore_codex_sub_costs EXIT

if [[ -f "$CODEX_SUB_COSTS_FILE" ]]; then
  CODEX_SUB_COSTS_EXISTS=1
  CODEX_SUB_COSTS_BACKUP=$(mktemp)
  cp -p "$CODEX_SUB_COSTS_FILE" "$CODEX_SUB_COSTS_BACKUP"
fi

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
