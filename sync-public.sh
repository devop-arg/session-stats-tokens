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
# IMPORTANTE (incidente 2026-08-24): usar SIEMPRE `git rm --cached`.
# El `git rm -f` original fallaba cuando la DB venía como MODIFICACIÓN (M)
# del squash merge y dejaba la DB staged dentro del commit público.
# `--cached` opera solo sobre el índice y saca cualquier estado (A o M).
git rm --cached -f session_history.json session_history.db session_history_legacy_freeze.json 2>/dev/null || true
git rm --cached -f codex_sub_costs.json 2>/dev/null || true
# Los backups de DB pueden venir como M del squash o ya trackeados de antes.
git rm --cached -f 'db_backups/session_history_*.db' 'db_backups/*.db' 2>/dev/null || true

# Conflictos modify/delete (archivo modificado en main, borrado en public):
# para datos sensibles la única resolución válida es BORRARLO del índice.
# `git rm --cached` no resuelve entradas unmerged; esto sí.
for F in $(git diff --name-only --diff-filter=U 2>/dev/null); do
  case "$F" in
    session_history.json|session_history.db|session_history_legacy_freeze.json|codex_sub_costs.json|db_backups/*)
      echo "=== 4b. Resolviendo conflicto de dato sensible: $F (se borra) ==="
      git rm -f -- "$F" || true
      ;;
  esac
done

# Conflictos de contenido en archivos normales (code/doc/config): el squash de
# main -> public genera conflictos recurrentes porque public tiene historia
# propia. La resolución canónica es SIEMPRE la versión de main (la fuente).
for F in $(git diff --name-only --diff-filter=U 2>/dev/null); do
  echo "=== 4c. Resolviendo conflicto de contenido: $F (gana main) ==="
  git checkout --theirs -- "$F" && git add -- "$F" || {
    echo "ERROR: no se pudo resolver $F automáticamente"
    exit 1
  }
done

if git diff --name-only --diff-filter=U | grep -q .; then
  echo "ERROR: quedan conflictos no resueltos después de excluir datos sensibles"
  git diff --name-only --diff-filter=U
  exit 1
fi

# `--cached` deja copias sin trackear en el working tree; borrarlas para que el
# checkout de vuelta a main no falle. (codex_sub_costs.json se restaura solo vía
# el trap restore_codex_sub_costs.)
rm -f session_history.json session_history.db session_history_legacy_freeze.json \
      db_backups/session_history_*.db db_backups/*.db 2>/dev/null || true

echo "=== 5. Commit merge ==="
git commit --no-edit -m "$MSG"

echo "=== 5b. VERIFICACIÓN ANTI-LEAK (pre-push, obligatoria) ==="
SENSITIVE_RE='^(session_history\.db|session_history\.json|session_history_legacy_freeze\.json|codex_sub_costs\.json|capture\.log)$|^db_backups/.*\.db$'
LEAKS=$(git ls-tree -r HEAD --name-only | grep -E "$SENSITIVE_RE" || true)
if [[ -n "$LEAKS" ]]; then
  echo "ERROR FATAL: el commit local contiene datos sensibles. NO se pushea:"
  echo "$LEAKS"
  echo "Revisar el paso 4 y rehacer el commit."
  exit 1
fi
echo "OK: árbol sanitizado."

echo "=== 6. Push a origin/public ==="
git push origin public

echo "=== 7. Force-push a origin/main (sanitizado) ==="
git push origin public:main --force

echo "=== 7b. VERIFICACIÓN REMOTA POST-PUSH (obligatoria) ==="
SYNC_FAIL=0
for REF in origin/public origin/main; do
  REMOTE_LEAKS=$(git ls-tree -r "$REF" --name-only | grep -E "$SENSITIVE_RE" || true)
  if [[ -n "$REMOTE_LEAKS" ]]; then
    echo "ERROR FATAL: $REF contiene datos sensibles DESPUÉS del push:"
    echo "$REMOTE_LEAKS"
    SYNC_FAIL=1
  else
    echo "OK: $REF sin datos sensibles."
  fi
done
if [[ "$SYNC_FAIL" -ne 0 ]]; then
  echo "ACCIÓN INMEDIATA: force-pushear una versión sanitizada y avisar al dueño."
  exit 1
fi

echo "=== 8. Volver a $BRANCH_CURRENT ==="
# -f por si el cron de captura recreó algún archivo sensible durante la sync.
git checkout -f "$BRANCH_CURRENT"

echo "=== OK ==="
