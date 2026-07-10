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

## `model_costs.json` (precios)

- Editado por la UI web (`/models`) y por `session-stats-models`.
- `session-stats --capture-all` auto-sembra modelos usados sin precio en `0/0/0`.
- **Backup automático**: antes de cada guardado la UI copia el archivo actual a
  `model_backups/model_costs_<timestamp>.json`.
- **Escritura**: in-place (truncate + write + fsync) bajo `fcntl.flock` en
  `model_costs.json.lock`. No usar `os.replace`/`tempfile`: en este entorno
  falla con `EBUSY` dentro del proceso uvicorn.
- **Si se corrompe** (parseo JSON inválido): restaurar la última copia buena
  desde `model_backups/`; el save devuelve error 500 claro si el archivo está
  corrupto en lugar de corromperlo.

## Migraciones SQLite

`session-stats` y `stats-web` deben ejecutar `init_db()` al arrancar para aplicar
migraciones no destructivas sobre bases existentes. Si una DB restaurada falla
con `no such column: cache_read_tokens`, ejecutar:

```bash
python3 -c 'import stats_common; stats_common.init_db()'
session-stats --capture-all
```
