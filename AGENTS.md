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

## OpenCode v2 (`opencode2`)

`opencode2` es el CLI v2 de OpenCode (`@opencode-ai/cli`, binario `~/.local/bin/opencode2`).
**Comparte la misma DB** (`~/.local/share/opencode/opencode.db`) con opencode v1
(`opencode-ai` 1.x) pero con tablas propias:

| Dato | v1 (opencode) | v2 (opencode2) |
|------|---------------|----------------|
| Sesiones | tabla `session` | tabla `session_v2` (contiene TODAS, incl. migradas) |
| Mensajes | tabla `message` (JSON con `role`, modelo en `model.modelID`) | tabla `session_message` (columna `type` en vez de `role`; modelo en `model.id`) |

- **Lectura dual con dedupe**: `get_opencode_sessions()` /
  `get_opencode_sqlite_sessions()` leen `session_v2` + `session` (dedupe por id,
  prevalece v2) y los mensajes de `session_message` + `message` (dedupe por
  `data_str` para no duplicar los mensajes migrados de v1→v2).
- **Upsert de la sesión activa**: desde 2026-08-14 la sesión de opencode con
  `time_updated` más reciente se persiste SIEMPRE (`_save_upsert`) en cada
  `--capture-all` (cron cada 5 min o manual), porque las sesiones v2 viven
  abiertas mucho tiempo y con skip-if-exists quedaban congeladas en el primer
  capture. El resto de las sesiones sigue con skip if exists (captura única).
- `has_real_usage_sqlite` consulta `session_message` primero y cae a `message`
  si la tabla no existe (DB de v1 puro).
- El filtro de mensajes usa `role` (v1) o ausencia de `role` + columna
  `type='assistant'` (v2).

### ⚠️ Dedupe v1/v2 por ID de mensaje (fix 2026-08-14)

La migración opencode v1→v2 **copia** sesiones y mensajes (mismos `id`) pero
**transforma el formato del `data`** (v1: `role/parentID/modelID` → v2:
`type/content`). Por eso el dedupe por `data_str` da **0 coincidencias** y el
cron contaba cada mensaje migrado **2 veces** (requests/tokens/costos x2 para
~250 sesiones tras la reinstalación de opencode2).

**Fix**: las 3 funciones que leen mensajes (`get_opencode_sqlite_sessions` en
`stats_common.py`, `has_real_usage_sqlite` y `get_session_stats_sqlite` en
`session-stats`) dedupean por **`id` de mensaje** (`SELECT id, data FROM ...`)
además de `data_str`. Al tocar cualquiera de esas funciones, mantener AMBOS
dedupes (por id entre tablas, por data_str dentro de la misma tabla).

**Recuperación de una DB duplicada**: comparar contra el backup diario
(`db_backups/`), borrar solo las sesiones que existen en la fuente
(`SELECT id FROM session_v2 UNION SELECT id FROM session`) — las sesiones de la
era JSON (v1.1.x) viven SOLO en `session_history.db` y se pierden si se borran
(no son re-capturables). Re-capturar con `--capture-all`.

### Limpieza de opencode.db (2026-08-14)

- Borradas las 36 sesiones de abril (session_v2/session_message/part/message) +
  VACUUM → opencode.db pasó de 955 MB a 373 MB. El historial ya estaba
  capturado en session_history.db (el dashboard no pierde nada).
- Vacía la tabla v1 (`message`/`session`): eran copias duplicadas de los
  mensajes migrados (~15 MB). session-stats la maneja con try/except.
- opencode v1 sigue instalado (`~/.local/bin/opencode`): si se abre, verá el
  historial v1 vacío (todo lo suyo está migrado a v2).

## Auth del dashboard (cookie de sesión)

- **Reemplaza al Basic Auth de nginx**: login por cookie firmada `stats_session`
  (90 días) vía endpoint `/login`; nginx valida con `auth_request` → `/__auth`.
- **Secreto de firma**: `stats-web/.session_secret` (gitignored, 600). Si se
  borra o cambia, todas las cookies quedan inválidas (hay que re-loguear).
- **Credenciales**: el backend valida contra `/etc/nginx/.htpasswd-stats`
  (Apache `$apr1$`, requiere `passlib` instalado en `~/.local`).
- **Si un backup/restore mueve `stats-web/` a otra máquina**, regenerar el
  `.session_secret` (o copiarlo junto con el directorio) para no invalidar
  sesiones existentes.
