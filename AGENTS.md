# session-stats — agent instructions

## ⚠️ CRÍTICO: Archivos NO trackeados en git público

- `session_history.db` — Base de datos con todas las sesiones históricas
- `session_history.json` — Respaldo JSON de sesiones

Estos archivos están en `.gitignore` (el repo público no trackea datos de usuario).
El repo PRIVADO (`private` remote) sí los trackea para backup.

## Reglas de oro

1. **ANTES de cualquier `git rebase`, `git stash pop`, `git reset --hard`, `git clean -f`:**
   ```bash
   cp session_history.db session_history.db.bak.$(date +%Y%m%d_%H%M%S)
   cp session_history.json session_history.json.bak.$(date +%Y%m%d_%H%M%S)
   ```
   Son 3 segundos. Hacelo siempre.

2. **NUNCA resolver conflicto `modify/delete` con `git rm` a ciegas.**
   Si un stash pop muestra "deleted by us", el archivo se perdió. Recuperarlo del stash:
   ```bash
   git checkout stash@{0} -- session_history.db
   ```

3. **Si algo sale mal**, el backup automático está en `db_backups/session_history_YYYYMMDD_060001.db` (diario a las 06:00). Restaurá desde ahí y recapturá con `session-stats --capture-all`.

4. **Los datos de Hermes viven en `~/.hermes/state.db`** (130MB). Ese archivo NUNCA se toca. Es la fuente de verdad para recapturar sesiones de Hermes.

## Flujo seguro para sincronizar cambios al repo

```bash
# 1. Backup
cp session_history.db session_history.db.bak
# 2. Verificar estado
git status --short
# 3. Si hay conflicto potencial, resolver sin perder archivos
# 4. Commit + push
```

## Recuperación de desastres

Si `session_history.db` se corrompe/vacía:
1. Restaurar último backup: `cp db_backups/session_history_YYYYMMDD_060001.db session_history.db`
2. Recapturar: `session-stats --capture-all`
3. Push al repo privado: `git add -f session_history.db && git commit -m "chore: restore db" && git push private main`
