# session-stats

> **Mantener actualizado.** Si cambian paths, archivos críticos o procedimientos de recuperación, editar este archivo y commitear.

## Publicación al público (a prueba de boludos)

> **Regla dura (incidente 2026-08-24)**: la rama canónica del repo público
> es **`origin/public`**, NO `origin/main`. `origin/main` es un espejo
> sanitizado que mantiene el script `sync-public.sh`.

La protección **no depende de leer documentación**: está automatizada en dos
barreras duras.

### Barrera 1 — hook `pre-push` (`hooks/pre-push`, vía `core.hooksPath`)

Corre en TODO `git push`, venga de donde venga:

- Push a `origin` con datos sensibles (`session_history.db/json`,
  `codex_sub_costs.json`, `db_backups/*.db`, `capture.log`) en el árbol → **RECHAZADO**.
- Push a `private/main` sin `session_history.db` → **RECHAZADO** (evita commits incompletos).

Saltearlo requiere `--no-verify` explícito. Si un agente lo usa sin causa
justificada, es una violación grave. El hook está versionado en `hooks/`;
si se reclona el repo, reactivarlo con `git config core.hooksPath hooks`.

### Barrera 2 — verificaciones dentro de `sync-public.sh`

El script se auto-verifica: chequeo anti-leak del commit ANTES de pushear
(paso 5b) y de los remotos DESPUÉS (paso 7b). Si falla, aborta sin pushear.

### Flujo correcto

1. Trabajar y commitear en `main` (trackea `private/main`). Si vas a tocar el
   propio `sync-public.sh` u otro archivo trackeado, **commitear ANTES de
   correr el script**: su paso 2 hace `checkout public --force` y descarta
   cambios sin commitear (pasó de verdad: el script se borró su propio fix).
2. `git push private main` — respaldo completo (con DB).
3. `./sync-public.sh ["mensaje"]` — publica al público SIN datos sensibles.

Nunca `git push origin <cualquier cosa>` a mano. No hace falta: el paso 3
hace todo y verifica solo.

### Detalle técnico por el que se filtró la DB (para no olvidarlo)

El bug original era `git rm -f` después del `merge --squash`: cuando la DB
venía como MODIFICACIÓN (M) del squash, el `git rm -f` fallaba silenciosamente
(la DB tenía cambios locales del cron cada 5 min) y el commit público salía
con la DB adentro. Ahora el script usa `git rm --cached -f` (saca del índice
cualquier estado A/M) más resolución explícita de conflictos modify/delete.
**No volver a `git rm -f`.**

## ⚠️ `session_history.db` y datos sensibles

- **Público (`origin`): JAMÁS.** Ni trackeado ni forzado. El `.gitignore` lo
  excluye; si necesitás `-f` para subirlo a `origin`, ALGO ESTÁ MAL: frenar.
- **Privado (`private`): sí, trackeado.** Desde el working tree se commitea con
  `git add -f session_history.db` (el `-f` es necesario porque el `.gitignore`
  lo ignora globalmente) y se verifica post-push:
  ```bash
  git ls-tree -r private/main --name-only | grep session_history.db
  ```
- **Cron `*/5 * * * * --capture-all` toca la DB constantemente**: puede dejar
  la DB "modificada" en cualquier momento y hacer fallar `git rm`/`add`/push.
  Ante ese fallo, usar las formas forzadas (`git add -f`, `git rm -f`,
  `git checkout -f`) sabiendo por qué se usan.
- Operaciones destructivas (`reset --hard`, `stash pop`, `rebase`) pueden
  borrarla sin aviso. Antes: `cp session_history.db /tmp/session_history.db.bak`.
  Si ya se borró: restaurar desde `db_backups/` + `session-stats --capture-all`.

## Lecciones del incidente 2026-08-24

1. **Leer TODA la sección "Repository Strategy" del README antes de cualquier
   operación git** — no la primera línea. El error original fue pushear a
   `origin/main` directo sin haber leído que la canónica es `origin/public`.
2. **Verificar el árbol remoto post-push SIEMPRE** (`git ls-tree -r <ref>`),
   aunque el push haya "salido bien". Un push exitoso puede llevarse datos
   sensibles adentro.
3. **Ante fallo "raro" de git (rm que no borra, add que ignora), investigar la
   causa real** — casi siempre hay un `.gitignore`, un estado unmerged o el
   cron de captura en el medio.

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
