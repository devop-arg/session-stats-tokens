# session-stats

> **Mantener actualizado.** Si cambian paths, archivos críticos o procedimientos de recuperación, editar este archivo y commitear.

## ⚠️ `session_history.db` y `session_history.json`

- **NUNCA commitear a `origin`** (repo público)
- **Sí trackear en `private`** con `git add -f` (repo de backup)

Cualquier operación git destructiva (`rebase`, `stash pop`, `reset --hard`) los puede borrar sin aviso.

**Antes de esas operaciones, siempre:**
```bash
cp session_history.db /tmp/session_history.db.bak
```

**Si ya se borró:** restaurar desde `db_backups/` + `session-stats --capture-all`.

## Migraciones SQLite

`session-stats` y `stats-web` deben ejecutar `init_db()` al arrancar para aplicar
migraciones no destructivas sobre bases existentes. Si una DB restaurada falla
con `no such column: cache_read_tokens`, ejecutar:

```bash
python3 -c 'import stats_common; stats_common.init_db()'
session-stats --capture-all
```
