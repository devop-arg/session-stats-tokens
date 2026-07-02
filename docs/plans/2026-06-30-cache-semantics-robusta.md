# Plan de ejecución: semántica robusta de cache y tokens facturables

> **Para agente jr:** ejecutar en orden, no saltear validaciones, no inventar semántica. Si una fuente no expone un dato, persistir `0` y documentarlo en el commit o en el reporte final.

**Objetivo:** dejar de usar heurísticas sobre `cache_tokens` y pasar a un modelo explícito por fuente para calcular costo, `price_per_1m`, `cache_ratio` y `billable_tokens` correctamente desde ahora en adelante.

**Arquitectura:** extender el schema SQLite con `cache_read_tokens`, `cache_write_tokens`, `billing_input_includes_cache_read` y `billing_mode`; adaptar todos los extractores para poblar esos campos; recalcular costos por fila `model_usage`; exponer en API separadamente tokens crudos y tokens facturables.

**Regla de producto:**
- `tokens` = actividad cruda.
- `billable_tokens` = tokens usados para costo unitario.
- `cache_ratio` = sólo `cache_read_tokens` sobre input efectivo, nunca incluye writes.

---

## Fase 0: preparación y resguardo

### Tarea 0.1: verificar árbol y crear backup manual de DB

**Objetivo:** evitar pérdida de datos antes de tocar schema o migraciones.

**Archivos:**
- Verificar: `session_history.db`
- Crear backup en: `db_backups/`

**Paso 1:** verificar que existe la DB.

Run:
```bash
ls "/home/capw/scripts/session-stats/db_backups"
```

**Paso 2:** crear backup con timestamp.

Run:
```bash
cp "/home/capw/scripts/session-stats/session_history.db" "/home/capw/scripts/session-stats/db_backups/session_history_$(date +%Y%m%d_%H%M%S)_pre-cache-semantics.db"
```

**Paso 3:** anotar la ruta exacta del backup en el reporte final.

**Criterio de aceptación:** existe un `.db` nuevo en `db_backups/`.

---

## Fase 1: helpers y contrato interno

### Tarea 1.1: agregar helpers explícitos de tokens facturables

**Objetivo:** centralizar la lógica de facturación y evitar fórmulas duplicadas.

**Archivo:**
- Modificar: `stats_common.py` cerca de `calculate_cost()`

**Paso 1:** agregar helper:

```python
def effective_billable_tokens(
    input_tokens,
    output_tokens,
    cache_read_tokens=0,
    cache_write_tokens=0,
    input_includes_cache_read=False,
):
    total = (input_tokens or 0) + (output_tokens or 0)
    if not input_includes_cache_read:
        total += cache_read_tokens or 0
    total += cache_write_tokens or 0
    return total
```

**Paso 2:** agregar helper de input no cacheado para `cache_ratio`:

```python
def effective_input_with_cache_read(input_tokens, cache_read_tokens, input_includes_cache_read=False):
    if input_includes_cache_read:
        return input_tokens or 0
    return (input_tokens or 0) + (cache_read_tokens or 0)
```

**Paso 3:** agregar `calculate_cost_v2()`.

Firma mínima:

```python
def calculate_cost_v2(
    model,
    input_tokens,
    output_tokens,
    cache_read_tokens=0,
    cache_write_tokens=0,
    input_includes_cache_read=False,
):
```

**Implementación esperada:**
- usar `MODEL_COSTS` y `normalize_model_name()` igual que hoy.
- cobrar input siempre sobre `input_tokens`.
- cobrar output sobre `output_tokens`.
- cobrar cache sobre:
  - `cache_write_tokens` siempre.
  - `cache_read_tokens` sólo cuando `input_includes_cache_read` sea `False`.

**Paso 4:** dejar `calculate_cost()` como wrapper legacy, sin borrarlo todavía.

```python
def calculate_cost(model, input_tokens, output_tokens, cache_tokens=0):
    return calculate_cost_v2(
        model,
        input_tokens,
        output_tokens,
        cache_read_tokens=cache_tokens,
        cache_write_tokens=0,
        input_includes_cache_read=False,
    )
```

**Paso 5:** compilar sintaxis.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats_common.py"
```

**Criterio de aceptación:** `stats_common.py` compila y existen los 3 helpers nuevos.

### Tarea 1.2: definir el contrato `by_model` v2 en comentarios mínimos

**Objetivo:** que el siguiente implementador no vuelva a mezclar `cache` con `cache_read`.

**Archivo:**
- Modificar: `stats_common.py` en las funciones extractoras principales

**Paso 1:** agregar un comentario corto, una sola vez, arriba del primer extractor o arriba de `save_session()`:

```python
# by_model v2: input, output, cache_read, cache_write, reasoning, requests,
# billing_input_includes_cache_read, billing_mode
```

**Criterio de aceptación:** el contrato nuevo queda visible cerca del código de persistencia.

---

## Fase 2: schema y persistencia

### Tarea 2.1: extender schema sin romper DB existente

**Objetivo:** agregar columnas nuevas en `sessions` y `model_usage`.

**Archivo:**
- Modificar: `stats_common.py` función `init_db()`

**Paso 1:** mantener `CREATE TABLE IF NOT EXISTS` pero sumando las nuevas columnas en la definición base.

Nuevas columnas requeridas en `sessions`:
- `cache_read_tokens INTEGER NOT NULL DEFAULT 0`
- `cache_write_tokens INTEGER NOT NULL DEFAULT 0`
- `billing_input_includes_cache_read INTEGER NOT NULL DEFAULT 0`
- `billing_mode TEXT NOT NULL DEFAULT 'legacy_unknown'`

Nuevas columnas requeridas en `model_usage`:
- `cache_read_tokens INTEGER NOT NULL DEFAULT 0`
- `cache_write_tokens INTEGER NOT NULL DEFAULT 0`
- `billing_input_includes_cache_read INTEGER NOT NULL DEFAULT 0`
- `billing_mode TEXT NOT NULL DEFAULT 'legacy_unknown'`

**Paso 2:** agregar migración idempotente con `ALTER TABLE` protegida.

Patrón recomendado:

```python
def _ensure_column(conn, table, column, definition):
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
```
```

Llamarla desde `init_db()` para las 8 columnas nuevas.

**Paso 3:** ejecutar inicialización manual.

Run:
```bash
python - <<'PY'
from stats_common import init_db
init_db()
print('ok')
PY
```

**Paso 4:** verificar columnas.

Run:
```bash
sqlite3 "/home/capw/scripts/session-stats/session_history.db" "PRAGMA table_info(sessions);"
sqlite3 "/home/capw/scripts/session-stats/session_history.db" "PRAGMA table_info(model_usage);"
```

**Criterio de aceptación:** ambas tablas muestran las columnas nuevas.

### Tarea 2.2: adaptar `save_session()` al contrato nuevo

**Objetivo:** persistir correctamente los nuevos campos y derivar la sesión desde `by_model`.

**Archivo:**
- Modificar: `stats_common.py` función `save_session()`

**Paso 1:** extender la firma para aceptar opcionalmente:
- `cache_read_tokens=None`
- `cache_write_tokens=None`
- `billing_input_includes_cache_read=0`
- `billing_mode='legacy_unknown'`

**Paso 2:** antes del `INSERT`, derivar agregados de sesión desde `by_model` si están presentes:

```python
derived_cache_read = sum((m.get('cache_read', 0) or 0) for m in by_model.values())
derived_cache_write = sum((m.get('cache_write', 0) or 0) for m in by_model.values())
```

Regla:
- si la sesión no recibe esos campos explícitos, usar los derivados.
- `cache_tokens` legacy puede persistirse como `cache_read + cache_write` para compatibilidad temporal.

**Paso 3:** actualizar el `INSERT INTO sessions` y `ON CONFLICT` para las columnas nuevas.

**Paso 4:** actualizar el `INSERT INTO model_usage` para usar:
- `cache_tokens = cache_read + cache_write`
- `cache_read_tokens`
- `cache_write_tokens`
- `billing_input_includes_cache_read`
- `billing_mode`

**Paso 5:** compatibilidad mínima para datos viejos:
- si `mdata` trae sólo `cache`, interpretarlo como `cache_read`
- `cache_write = 0`

**Paso 6:** compilar.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats_common.py"
```

**Criterio de aceptación:** `save_session()` persiste el esquema nuevo sin romper llamadas existentes.

---

## Fase 3: extractores por fuente

### Tarea 3.1: Codex

**Objetivo:** capturar semántica explícita para Codex.

**Archivo:**
- Modificar: `stats_common.py` función `get_codex_session_stats()`

**Paso 1:** mantener los campos legacy si son usados por otras rutas, pero agregar nuevos campos al `result`:
- `cache_read`
- `cache_write`
- `billing_input_includes_cache_read`
- `billing_mode`

**Paso 2:** mapear:

```python
result['cache_read'] = last_token_count.get('cached_input_tokens', 0)
result['cache_write'] = 0
result['billing_input_includes_cache_read'] = 1
result['billing_mode'] = 'codex_cached_input'
result['cache'] = result['cache_read']
```

**Paso 3:** compilar.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats_common.py"
```

**Criterio de aceptación:** una sesión Codex nueva devuelve explícitamente `cache_read` y `billing_mode`.

### Tarea 3.2: OpenCode

**Objetivo:** capturar `cache.read` y, si existe, `cache.write`.

**Archivo:**
- Modificar: `stats_common.py` función `get_opencode_sqlite_sessions()`

**Paso 1:** al leer `tokens`, extraer:

```python
cache_info = tokens.get('cache') or {}
cache_read = cache_info.get('read', 0) or 0
cache_write = cache_info.get('write', 0) or 0
```

**Paso 2:** cambiar `by_model[model]` para guardar:
- `cache_read`
- `cache_write`
- `cache` como suma temporal para compatibilidad
- `billing_input_includes_cache_read = 0`
- `billing_mode = 'opencode_separate_cache'`

**Paso 3:** cambiar el agregado de sesión:
- `total_cache_read`
- `total_cache_write`
- `cache = total_cache_read + total_cache_write`

**Paso 4:** agregar esos campos al `result[sid]`.

**Paso 5:** compilar.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats_common.py"
```

**Criterio de aceptación:** OpenCode deja de guardar sólo `cache.read` implícito.

### Tarea 3.3: Hermes

**Objetivo:** eliminar la inconsistencia entre sesión y `by_model`.

**Archivos:**
- Modificar: `stats_common.py` funciones `get_hermes_sessions()` y `get_hermes_session_stats()`

**Paso 1:** en `by_model`, reemplazar:

```python
'cache': cache_read
```

por:

```python
'cache_read': cache_read,
'cache_write': cache_write,
'cache': cache_read + cache_write,
'billing_input_includes_cache_read': 0,
'billing_mode': 'hermes_read_write_split',
```

**Paso 2:** mantener los campos de sesión alineados con eso.

**Paso 3:** buscar otros lugares en `stats_common.py` que asumen `m.get('cache', 0)` y reemplazarlos por una lectura tolerante:

```python
(m.get('cache_read', m.get('cache', 0)) or 0) + (m.get('cache_write', 0) or 0)
```

**Paso 4:** compilar.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats_common.py"
```

**Criterio de aceptación:** Hermes usa la misma semántica en sesión y en modelo.

### Tarea 3.4: revisar Cursor y Kilo

**Objetivo:** no dejar fuentes silenciosamente inconsistentes.

**Archivo:**
- Modificar: `stats_common.py` en extractores Cursor/Kilo si persisten `by_model`

**Paso 1:** buscar estructuras `by_model[...] = { ... }` y asegurarse de que, aunque no tengan cache real, persistan:
- `cache_read = 0`
- `cache_write = 0`
- `billing_input_includes_cache_read = 0`
- `billing_mode = 'no_cache'` o específico

**Paso 2:** compilar.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats_common.py"
```

**Criterio de aceptación:** todas las fuentes persistidas conocen el contrato v2.

---

## Fase 4: recálculo y migración histórica

### Tarea 4.1: crear script de migración de semántica

**Objetivo:** poblar columnas nuevas y recalcular costos desde la información disponible.

**Archivo:**
- Crear: `scripts/migrate-cache-semantics.py`

**Paso 1:** estructura del script:
- abrir DB
- llamar `init_db()`
- recorrer `sessions` + `model_usage`
- asignar semántica por `source`
- recalcular costos por fila con `calculate_cost_v2()`
- recalcular costo de sesión como suma de `model_usage.cost`
- emitir resumen final

**Paso 2:** reglas mínimas por `source`:
- `codex`: `cache_read = cache_tokens`, `cache_write = 0`, `billing_input_includes_cache_read = 1`, `billing_mode = 'codex_cached_input'`
- `opencode`: `cache_read = cache_tokens`, `cache_write = 0`, `billing_input_includes_cache_read = 0`, `billing_mode = 'opencode_separate_cache'`
- `hermes`: si no se puede separar histórico exacto, marcar `billing_mode = 'legacy_unknown'` y no fingir precisión
- otros: `billing_mode = 'legacy_unknown'` o `no_cache` según tokens

**Paso 3:** el script debe imprimir:
- filas `model_usage` actualizadas
- sesiones recalculadas
- filas `legacy_unknown`
- costo total antes y después

**Paso 4:** ejecutar el script.

Run:
```bash
python "/home/capw/scripts/session-stats/scripts/migrate-cache-semantics.py"
```

**Paso 5:** verificar muestreo SQL.

Run:
```bash
sqlite3 "/home/capw/scripts/session-stats/session_history.db" "SELECT source, billing_mode, COUNT(*) FROM sessions GROUP BY source, billing_mode ORDER BY source, billing_mode;"
sqlite3 "/home/capw/scripts/session-stats/session_history.db" "SELECT billing_mode, COUNT(*) FROM model_usage GROUP BY billing_mode ORDER BY billing_mode;"
```

**Criterio de aceptación:** las nuevas columnas quedan pobladas y el script reporta cuántas filas siguen inciertas.

### Tarea 4.2: rehacer el cálculo histórico agregado por fila

**Objetivo:** que el histórico no vuelva a calcular costo desde agregados ambiguos por modelo.

**Archivo:**
- Modificar: `stats_common.py` función `recalculate_historical_cost()`

**Paso 1:** donde hoy se agregan `input/output/cache` por modelo, empezar a agregar también:
- `cache_read`
- `cache_write`
- `billing_input_includes_cache_read`

**Paso 2:** para el costo total, dejar de hacer sólo:

```python
calculate_cost(model, mdata['input'], mdata['output'], mdata.get('cache', 0))
```

y reemplazarlo por suma por fila cuando la fila tenga v2.

**Paso 3:** si una fila es legacy y no tiene semántica explícita, usar fallback documentado:
- si `billing_mode == 'legacy_unknown'`, usar `calculate_cost()` legacy y no presentarlo como exacto

**Paso 4:** compilar.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats_common.py"
```

**Criterio de aceptación:** el histórico puede recalcular costo usando v2 donde exista.

---

## Fase 5: API backend

### Tarea 5.1: agregar helpers de agregación para la web

**Objetivo:** evitar repetir SQL ambigua en varios endpoints.

**Archivo:**
- Modificar: `stats-web/main.py`

**Paso 1:** importar desde `stats_common.py`:
- `effective_billable_tokens`
- `effective_input_with_cache_read`

**Paso 2:** crear helpers privados en `main.py`:

```python
def _row_billable_tokens(row):
    return effective_billable_tokens(
        row['input_tokens'],
        row['output_tokens'],
        row.get('cache_read_tokens', 0),
        row.get('cache_write_tokens', 0),
        bool(row.get('billing_input_includes_cache_read', 0)),
    )
```

Y otro para `cache_ratio`.

**Paso 3:** compilar.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats-web/main.py"
```

**Criterio de aceptación:** `main.py` tiene helpers reutilizables antes de tocar endpoints.

### Tarea 5.2: `/api/models`

**Objetivo:** exponer actividad cruda + tokens facturables.

**Archivo:**
- Modificar: `stats-web/main.py` endpoint `/api/models`

**Paso 1:** ampliar SELECT para incluir:
- `SUM(mu.cache_read_tokens)`
- `SUM(mu.cache_write_tokens)`
- una agregación coherente de `billing_mode` si hace falta sólo para debug

**Paso 2:** en Python, agregar a cada fila:
- `billable_tokens`
- `price_per_1m`

**Paso 3:** mantener `input_tokens`, `output_tokens`, `cache_tokens` por compatibilidad.

**Criterio de aceptación:** el endpoint entrega ambos universos: raw y billable.

### Tarea 5.3: `/api/token-cost`

**Objetivo:** usar sólo tokens facturables para `price_per_1m`.

**Archivo:**
- Modificar: `stats-web/main.py` endpoint `/api/token-cost`

**Paso 1:** eliminar cálculo directo con `SUM(input+output+cache)`.

**Paso 2:** consultar filas con:
- `model`
- `cost`
- `input_tokens`
- `output_tokens`
- `cache_read_tokens`
- `cache_write_tokens`
- `billing_input_includes_cache_read`

Ideal: si SQLite complica la agregación correcta por semántica, traer filas base y agregar en Python.

**Paso 3:** calcular:
- `total_tokens` = `billable_tokens`
- `price_per_1m` = `cost / billable_tokens`

**Paso 4:** overall igual: sumar `billable_tokens`, no tokens crudos.

**Criterio de aceptación:** ningún `price_per_1m` depende ya de `input + output + cache` sin semántica.

### Tarea 5.4: `/api/subscription-estimate`

**Objetivo:** que `cost_api` use `billable_tokens` reales.

**Archivo:**
- Modificar: `stats-web/main.py` endpoint `/api/subscription-estimate`

**Paso 1:** misma estrategia que en `/api/token-cost`.

**Paso 2:** `item['tokens']` debe ser `billable_tokens` si el campo se usa para costo unitario.

**Paso 3:** si necesitás preservar el total crudo, agregar otro campo:
- `raw_tokens`

**Criterio de aceptación:** la comparación de planes usa el denominador correcto.

### Tarea 5.5: `/api/cache-ratio`

**Objetivo:** usar sólo `cache_read_tokens`.

**Archivo:**
- Modificar: `stats-web/main.py` endpoint `/api/cache-ratio`

**Paso 1:** reemplazar `cache_tokens` por `cache_read_tokens`.

**Paso 2:** denominador:
- si `billing_input_includes_cache_read = 1`, usar `input_tokens`
- si no, usar `input_tokens + cache_read_tokens`

**Paso 3:** `cache_write_tokens` no participa.

**Criterio de aceptación:** ratio consistente entre Codex y OpenCode/Hermes.

### Tarea 5.6: `/api/today`, top models y leaderboard

**Objetivo:** distinguir claramente actividad y costo unitario.

**Archivo:**
- Modificar: `stats-web/main.py` secciones `/api/today` y `_build_top_models_payload()`

**Paso 1:** dejar `tokens` como actividad cruda para barras y porcentajes.

**Paso 2:** cuando se calcule `price_per_1m`, usar `billable_tokens`.

**Paso 3:** si el payload lo permite sin romper frontend, agregar:
- `billable_tokens`

**Criterio de aceptación:** chart y leaderboard no mezclan raw con facturable.

---

## Fase 6: frontend

### Tarea 6.1: revisar consumidores de `total_tokens` y `price_per_1m`

**Objetivo:** no dejar UI mostrando una etiqueta con semántica equivocada.

**Archivo:**
- Modificar: `stats-web/static/app.js`

**Paso 1:** revisar llamadas a:
- `/api/token-cost`
- `/api/cache-ratio`
- `/api/top-models`
- `/api/subscription-estimate`

**Paso 2:** si el backend pasa `billable_tokens`, usarlo en las vistas de costo.

Ejemplos:
- token cost cards: mostrar `m.total_tokens` si ahora representa billable, o renombrar en backend/frontend a `billable_tokens` y usar ese campo.
- leaderboard: si conserva `tokens` crudo, no tocar el texto salvo que haya confusión.

**Paso 3:** verificar que no haya `undefined` por campos nuevos.

**Criterio de aceptación:** dashboard carga sin errores JS y cada widget usa el campo correcto.

---

## Fase 7: CLI

### Tarea 7.1: `session-stats-period`

**Objetivo:** mostrar volumen crudo y costo con denominador correcto.

**Archivo:**
- Modificar: `session-stats-period`

**Paso 1:** localizar cualquier `input + output + cache` usado para costo unitario o total de costo.

**Paso 2:** agregar, si es simple, una línea separada:
- `Tokens:` crudos
- `Billable:` facturables

**Paso 3:** si no existe un cálculo fácil por agregados, leer filas `model_usage` y sumar `billable_tokens` por fila.

**Criterio de aceptación:** el CLI deja explícita la diferencia entre actividad y costo.

---

## Fase 8: verificación integral

### Tarea 8.1: validación de sintaxis

**Objetivo:** asegurar que no se rompió nada a nivel Python.

Run:
```bash
python -m py_compile "/home/capw/scripts/session-stats/stats_common.py"
python -m py_compile "/home/capw/scripts/session-stats/stats-web/main.py"
python -m py_compile "/home/capw/scripts/session-stats/scripts/migrate-cache-semantics.py"
python -m py_compile "/home/capw/scripts/session-stats/session-stats-period"
```

**Criterio de aceptación:** sin errores de sintaxis.

### Tarea 8.2: correr migración y recaptura

**Objetivo:** asegurar que los datos futuros y el histórico inmediato quedan consistentes.

Run:
```bash
python "/home/capw/scripts/session-stats/scripts/migrate-cache-semantics.py"
"/home/capw/scripts/session-stats/session-stats" --capture-all
```

**Criterio de aceptación:** captura completa sin tracebacks.

### Tarea 8.3: queries SQL de control

**Objetivo:** detectar filas mal migradas o costos imposibles.

Run:
```bash
sqlite3 "/home/capw/scripts/session-stats/session_history.db" "SELECT COUNT(*) FROM sessions WHERE cache_read_tokens < 0 OR cache_write_tokens < 0;"
sqlite3 "/home/capw/scripts/session-stats/session_history.db" "SELECT COUNT(*) FROM model_usage WHERE cost < 0;"
sqlite3 "/home/capw/scripts/session-stats/session_history.db" "SELECT source, SUM(cost) FROM sessions GROUP BY source ORDER BY 2 DESC;"
sqlite3 "/home/capw/scripts/session-stats/session_history.db" "SELECT billing_mode, COUNT(*) FROM model_usage GROUP BY billing_mode ORDER BY 2 DESC;"
```

**Criterio de aceptación:** sin negativos y con `billing_mode` poblado.

### Tarea 8.4: smoke test HTTP local

**Objetivo:** verificar que el dashboard sigue sirviendo JSON válido.

Si el servicio ya está corriendo, usar:

```bash
curl -s http://127.0.0.1:8091/api/token-cost
curl -s http://127.0.0.1:8091/api/cache-ratio
curl -s http://127.0.0.1:8091/api/subscription-estimate
curl -s http://127.0.0.1:8091/api/top-models
```

Si no está corriendo, documentar que la verificación quedó pendiente.

**Criterio de aceptación:** endpoints responden JSON y no 500.

---

## Orden recomendado de commits

1. `refactor: agregar helpers y schema v2 de cache`
2. `fix: normalizar extractores con cache read/write`
3. `feat: migrar costos y semantica historica`
4. `fix: usar billable_tokens en api web`
5. `fix: distinguir tokens crudos y facturables en cli`
6. `docs: agregar plan de semantica robusta de cache`

---

## Riesgos que el agente jr no debe ignorar

- No asumir que `cache_tokens` histórico puede separarse siempre en read/write.
- No presentar `legacy_unknown` como exacto.
- No usar `cache_write_tokens` en `cache_ratio`.
- No recalcular costos por modelo agregado si hay mezcla de fuentes.
- No romper compatibilidad de payload sin revisar `stats-web/static/app.js`.

---

## Definición de terminado

Se considera terminado sólo si se cumple todo esto:

- DB con columnas nuevas en `sessions` y `model_usage`
- extractores persisten `cache_read`, `cache_write`, `billing_mode`
- `calculate_cost_v2()` y `effective_billable_tokens()` están en uso real
- migración histórica ejecutable y probada
- `/api/token-cost`, `/api/subscription-estimate` y `/api/cache-ratio` ya no usan `input + output + cache` directo
- frontend sigue cargando
- CLI distingue raw vs billable o documenta la limitación explícitamente
