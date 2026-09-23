# Cache ratio por sesiones elegibles — Plan de implementación

> **Para Hermes:** ejecutar con `subagent-driven-development` únicamente después de aprobar este plan. La revisión de Luna es previa a cualquier implementación.

**Objetivo:** calcular el ratio de cache global y por modelo usando sesiones elegibles, excluyendo del ratio las sesiones con `requests >= 5` y cache ratio menor a `5%`, sin modificar consumo, costos ni histórico.

**Arquitectura:** la sesión completa es la unidad de elegibilidad. `sessions.requests` es el contador canónico de sesiones persistidas; para sesiones externas se usan los contadores `stats["requests"]`/`sess["requests"]`. El cache read y el denominador se normalizan por cada fila `model_usage` antes de sumar, para no perder fallbacks legacy al mezclar modelos o read/write. Luego las filas de las sesiones elegibles se agregan globalmente y por modelo. Las sesiones mixtas se incluyen o excluyen completas. No se resuelve `provider` ni se consulta `state.db`.

**Stack:** Python 3 + SQLite + FastAPI; tests focales con `unittest`; dashboard en `stats-web/main.py`.

---

## Contrato

### Alcance

- Reemplazar la política actual por modelo/provider en todas las métricas de ratio:
  - `stats_common.recalculate_historical_cost()` y el ratio usado por el CLI/header.
  - `/api/summary`.
  - `/api/today-summary` y su ratio por modelo.
  - `_build_top_models_payload()` (`/api/top-models` y `/api/top-models-30d`).
  - `/api/cache-ratio`.
- Mantener una sola implementación de la regla y reutilizarla en histórico y web.
- Mantener los acumuladores de tokens, requests, costos y cantidad de sesiones sin filtrar.
- Actualizar los tests focales y el apartado de cache ratio del README.
- Actualizar los textos visibles de la sección de cache en `dashboard.html` y en ambos idiomas de `i18n.js` para que no describan la métrica como “modelos con cache”.

### Fuera de alcance

- No modificar `session_history.db`, `~/.hermes/state.db` ni datos históricos.
- No modificar precios, aliases, costos ni la captura de sesiones.
- No persistir una marca de sesión elegible/excluida: una sesión activa puede cambiar cuando recibe más requests o cache.
- No agregar providers a `session_history.db`.
- No cambiar layout, CSS ni comportamiento de la UI; sí cambiar los labels y títulos de la sección de cache. Los endpoints conservarán sus campos existentes.
- No hacer deploy, reiniciar `session-stats-web`, commit ni push como parte de este plan.

### Regla exacta

Para cada sesión:

```python
eligible = requests < 5 or session_cache_ratio >= 5.0
```

El umbral es estricto: exactamente `5.0%` se conserva. Para sesiones con `requests >= 5` y denominador cero, el ratio es `0%` y se excluyen.

El `session_cache_ratio` se calcula con:

```python
cache_read = effective_cache_read_tokens(
    cache_tokens, cache_read_tokens, cache_write_tokens
)
denominator = effective_cache_ratio_input(
    source, input_tokens, cache_read
)
ratio = cache_read / denominator * 100 if denominator else 0.0
```

La comparación contra `5.0` usa el valor no redondeado; el redondeo ocurre solo al formar el payload visible. La semántica existente se conserva: Codex usa el input que ya incluye cache; las demás fuentes usan input más cache read. **Actualización 2026-09-23 (decisión del dueño)**: para las fuentes que facturan el cache write aparte y no incluyen cache en el input (claude, hermes), el cache write también suma al denominador como cache miss facturado (`effective_cache_ratio_input` y su espejo SQL `_sql_cache_ratio_input`). El fallback legacy de `cache_tokens` sí produce cache read cuando read/write son cero.

Una vez elegible una sesión, todas sus filas `model_usage` participan del ratio del modelo, incluidos sus cache misses. Una sesión multi-modelo se filtra completa, según la decisión del dueño.

---

## Evidencia del estado actual

El repo está en `/home/capw/scripts/session-stats`, rama `main`, tracking `private/main`, HEAD local `cd4dc33`. El worktree ya contiene un delta local previo, todavía no publicado:

```text
M  README.md
M  model_aliases.json              # cambio ajeno al ratio; preservar
M  model_costs.json                # cambio ajeno al ratio; preservar
M  session_history.db              # cambio del cron/datos; no tocar
M  stats-web/main.py
M  stats_common.py
?? stats-web/tests/test_cache_ratio.py
```

Antes de implementar se debe respaldar el estado actual de los archivos críticos y revisar el diff. El nuevo corte debe reemplazar únicamente la variante previa de modelo/provider creada en `stats_common.py`, `stats-web/main.py`, README y el test; no debe resetear ni sobrescribir los tres cambios ajenos.

Hallazgos concretos:

- `stats_common.py:1527-1606` implementa actualmente `calculate_observed_cache_ratio()` por identidad `(modelo normalizado, provider)`.
- `stats_common.py:1483-1524` implementa `get_hermes_model_provider_index()` para recuperar providers desde `state.db`; con la política de sesión deja de ser necesario.
- `stats_common.py:1688-1727`, `1795-1802`, `1830-1837` y `1874-1885` construyen `cache_ratio_rows`; `stats_common.py:1915` calcula el ratio histórico desde esas filas.
- `stats-web/main.py:81-100` resuelve providers Hermes y llama la política modelo/provider.
- `/api/summary` obtiene ratio en `stats-web/main.py:402-442`.
- `/api/today-summary` conserva consumo completo en `:507-524`, pero calcula el ratio por modelo sin filtrar en `:538-586`.
- `_build_top_models_payload()` agrupa por modelo en `:1042-1059` y calcula ratios sin filtro en `:1159-1181`.
- `/api/cache-ratio` en `:1287-1334` filtra filas con cache positivo antes de agregar, por lo que no puede incluir misses de una sesión elegible.
- `stats-web/tests/test_cache_ratio.py` contiene cuatro casos para la política anterior por modelo/provider y debe reorientarse al contrato de sesión.
- `README.md:102-115` documenta la política anterior por `(modelo normalizado, provider)` y debe actualizarse.
- `stats-web/templates/dashboard.html:250-270` y `stats-web/static/i18n.js:73-78,247-251` todavía muestran “modelos con cache” y deben nombrar sesiones elegibles.
- `stats_common.py:715-749` y `:867-874` ya tienen consultas dentro de lectores externos por sesión; no son creadas por este cambio y quedan fuera de la optimización de elegibilidad, salvo que la implementación necesite tocarlas por un fallo demostrado.

---

## Tareas de implementación

### Tarea 1: fijar la política pura y sus tests

**Objetivo:** expresar la elegibilidad de sesión en una función reutilizable, sin SQL ni providers.

**Archivos:**

- Modificar: `stats_common.py` alrededor de `effective_cache_ratio_input()` y `calculate_observed_cache_ratio()`.
- Modificar: `stats-web/tests/test_cache_ratio.py`.

**Pasos TDD:**

1. Reemplazar los tests de identidad modelo/provider por casos de sesión:
   - `4 requests`, ratio `0%` → elegible.
   - `5 requests`, ratio `4.99%` → excluida.
   - `5 requests`, ratio exactamente `5%` → elegible.
   - Una sesión con dos modelos, ratio agregado menor al `5%` aunque uno de sus modelos individualmente supere `5%` → se excluyen ambas filas.
   - Dos sesiones: una excluida y otra elegible; solo las filas de la elegible entran al global y al modelo.
   - Codex conserva su denominador especial y usa el contador global `sessions.requests`, no la suma de requests por modelo.
   - Fallback legacy `cache_tokens` funciona cuando read/write son cero; cache-write-only no cuenta como hit.
   - Denominador cero con `requests >= 5` excluye y con `requests < 5` incluye.
   - `4.99%` excluye y `5.0%` incluye sin redondear antes de comparar.
   - Una sesión elegible con una fila hit y otra miss conserva el miss en el denominador; una sesión inelegible con hit descarta todo.
   - Mezcla de filas legacy/read-write en una misma sesión normaliza cada fila antes de agrupar.
2. Ejecutar el test y observar RED contra la política actual.
3. Implementar helpers puros, preferentemente con responsabilidades separadas:
   - una función que calcula `cache_read`, denominador y ratio de una sesión;
   - una función que determina `eligible` con `requests < 5` o ratio `>= 5`;
   - una función agregadora que recibe filas de `model_usage` enriquecidas con los datos de su sesión, normaliza cada fila y devuelve ratio global y ratios por modelo usando solo sesiones elegibles.
   - La entrada debe contener explícitamente `session_id`, `session_requests`, `session_source`, los tres campos cache de sesión/modelo y los contadores de modelo; no debe inferir `session_requests` sumando `model_usage.requests`.
4. La agregación debe devolver también conteos de sesiones elegibles/excluidas para que puedan probarse, aunque no sea obligatorio exponerlos aún en la API.
5. Ejecutar nuevamente el test focal y verificar GREEN.

**Invariantes:** la función no hace I/O, no mira `provider`, no modifica filas, y la exclusión nunca afecta tokens/costos.

### Tarea 2: integrar la elegibilidad en el recálculo histórico

**Objetivo:** que `recalculate_historical_cost()` aplique la política de sesión al ratio del header/CLI sin tocar sus acumuladores generales.

**Archivos:**

- Modificar: `stats_common.py:1609-1917`.

**Pasos:**

1. En la consulta `model_usage` existente, proyectar `session_id`, `s.requests` como contador canónico, `s.source` y los contadores agregados de sesión necesarios. Para el cache del ratio, calcular `effective_cache_read_tokens()` y `effective_cache_ratio_input()` por cada fila de `model_usage` antes de agrupar por `session_id`; no aplicar el fallback después de sumar filas heterogéneas.
2. Construir un mapa de elegibilidad por `session_id` en memoria, con una sola decisión por sesión y sin consultas dentro del loop. Si las filas de modelo contradicen los agregados de `sessions`, los agregados de sesión siguen gobernando el contador de requests y el cache ratio debe basarse en las filas de modelo normalizadas.
3. Mantener `models_totals`, `total_requests`, `total_input`, `total_output`, `total_tokens`, `total_cache_read` y costos exactamente con todas las sesiones.
4. Agregar a las filas del ratio únicamente los `model_usage` pertenecientes a sesiones elegibles.
5. Para sesiones Codex/OpenCode/Hermes externas que todavía no estén en `session_history.db`, calcular su elegibilidad una vez con el objeto de sesión ya cargado (`stats`/`sess`) y normalizar cada fila de modelo antes de agregar todos sus modelos o ninguno.
6. Mantener `historical_total` y `legacy_price_adjustment` fuera de elegibilidad y ratio, como hoy. Tratar `kilocode_legacy` según su naturaleza de sesión real solo si aparece en el resultset; no convertir el agregado sintético en una sesión elegible.
7. Eliminar el uso de `get_hermes_model_provider_index()` y la identidad provider del cálculo. Si queda sin consumidores, eliminarlo dentro del mismo delta.
8. Hacer que el resultado `cache_ratio` use el agregador nuevo. No cambiar `total_cache_read` ni los costos.

**Gate:** una ejecución de `recalculate_historical_cost()` sobre la DB real debe mostrar el nuevo ratio y exactamente los mismos totales de input/output/cache/costo que la lectura previa del contrato. La ejecución es read-only respecto de la DB. El plan no afirma que todo el recálculo tenga cantidad fija de queries: los lectores externos conservan consultas por sesión preexistentes; el requisito de no N+1 aplica a la nueva elegibilidad y a las consultas del dashboard.

### Tarea 3: integrar resumen global y resumen diario

**Objetivo:** que `/api/summary` y `/api/today-summary` filtren ratios por sesión, pero mantengan los consumos completos.

**Archivos:**

- Modificar: `stats-web/main.py:81-100`, `:359-447` y `:450-600`.

**Pasos:**

1. Reemplazar `_observed_cache_ratio()` por una llamada al agregador de sesión; quitar imports de provider/index que ya no tengan consumidores.
2. En `/api/summary`, enriquecer la consulta de `ratio_rows` con los contadores agregados de `sessions`. Calcular una vez la elegibilidad y usar el resultado para `cache_ratio` global.
3. En `/api/today-summary`, conservar la consulta `models` sin filtro para que `top_models`, tokens, costos y porcentajes sigan representando todo el consumo. Calcular por separado `ratio_by_model` con las filas de sesiones elegibles.
4. Al construir cada modelo, tomar su ratio del acumulador elegible; si no tiene filas elegibles con denominador, devolver `0.0` manteniendo el contrato actual del campo.
5. Calcular `cache_ratio` global con la misma selección de sesiones elegibles, evitando que el ratio del header y el diario diverjan por usar reglas diferentes.
6. No ejecutar un `SELECT` por cada sesión. Las consultas deben ser de cantidad fija y la lógica por sesión debe ser un recorrido en memoria sobre el resultset.

**Acceptance:** con fixtures SQLite temporales que tengan una sesión B.AI grande con ratio `0%`, otra sesión con cache alto, una sesión elegible con hit+miss y una sesión mixta, el ratio global y el ratio de cada modelo deben ignorar únicamente las sesiones inelegibles; los campos `total_input_tokens`, `total_tokens`, `total_cost`, `requests` y `top_models` deben seguir incluyendo todas. El fixture debe comparar el payload de `/api/summary` y `/api/today-summary`, no solo el helper.

### Tarea 4: integrar top-models y `/api/cache-ratio`

**Objetivo:** eliminar las dos rutas restantes que calculan ratios sin la política de sesión.

**Archivos:**

- Modificar: `stats-web/main.py:1020-1202`.
- Modificar: `stats-web/main.py:1287-1334`.

**Pasos:**

1. En `_build_top_models_payload()`, dejar intactos `model_rows`, series temporales, tokens, costos y ranking. Agregar una lectura por lote de filas `model_usage` con `session_id`, `s.requests`, `s.source` y cache por modelo; construir el agregador global y `ratio_by_model` usando solo sesiones elegibles y normalización por fila.
2. Usar el agregador elegible para ambos campos: `leaderboard[].cache_ratio` y el `cache_ratio` global del payload devuelto por `/api/top-models` y `/api/top-models-30d`. No usar `agg` bruto para ninguno de esos dos ratios.
3. En `/api/cache-ratio`, quitar el filtro SQL que descarta previamente las filas sin cache positivo, proyectar `session_id`, `s.requests`, `s.source` y los cache counters, resolver elegibilidad una vez por sesión y agregar por modelo únicamente filas de sesiones elegibles. Una sesión elegible puede tener misses que deben permanecer en su denominador; una sesión inelegible con hit no aporta nada.
4. Agrupar todas las filas de sesiones elegibles por modelo normalizado; exponer modelos con cache positivo siguiendo el comportamiento actual del endpoint, pero calcular su denominador con todos los modelos de esas sesiones elegibles.
5. Mantener la semántica actual de `uncached`, `cached`, umbral de un millón de tokens y ordenamiento, salvo el nuevo filtro de sesión.
6. Verificar que no haya otros consumidores de `calculate_observed_cache_ratio`, `_observed_cache_ratio` o `get_hermes_model_provider_index` mediante búsqueda global. Si se cambia el nombre del helper, buscar también el nombre nuevo y revisar `/api/cache-ratio` explícitamente.

**Acceptance:** el mismo fixture debe producir el mismo ratio global y ratio de modelo en `/api/today-summary`, `/api/top-models-30d`, `/api/top-models` y `/api/cache-ratio`; ninguna ruta debe incluir la sesión excluida en los ratios. En `summary`, `today-summary`, `top-models` y `top-models-30d` deben permanecer iguales tokens, costos, requests, ranking y series. En `/api/cache-ratio`, `cached`, `uncached`, `input_tokens` y `cache_tokens` son componentes derivados del conjunto elegible y deben cambiar coherentemente; se conserva la forma del payload, el umbral de 1M y el ordenamiento.

### Tarea 5: documentación y limpieza del delta

**Objetivo:** que el README y el código describan una sola política, sin residuos del enfoque provider-specific.

**Archivos:**

- Modificar: `README.md:102-120`.
- Modificar: `stats-web/templates/dashboard.html:23-25,66-69,105-108,158-161,250-270`.
- Modificar: `stats-web/static/i18n.js:27,74-78,206,248-251`.
- Revisar/eliminar solo el código muerto creado por el delta previo en `stats_common.py` y `stats-web/main.py`.

**Contenido requerido:**

- La unidad es la sesión completa.
- `requests < 5` se incluye siempre.
- Con `requests >= 5`, ratio menor a `5%` se excluye del ratio.
- Las sesiones mixtas se filtran completas intencionalmente.
- Tokens, costos y requests no se filtran.
- La métrica debe rotularse/documentarse como ratio sobre sesiones elegibles, no como ratio bruto de todo el consumo.
- No mencionar providers como criterio de exclusión.
- Los labels en español e inglés deben mencionar sesiones elegibles y, si el copy lo permite sin sobrecargarlo, el umbral de `5 requests / 5%`.
- `card.cache_ratio` se reutiliza en las tarjetas global, diaria, 30 días y anual; actualizar esa clave en ambos idiomas para que todas queden inequívocamente rotuladas como ratio de sesiones elegibles. La sección detallada `cache.*` debe usar el mismo concepto.

### Tarea 6: gates y verificación final

**Objetivo:** demostrar comportamiento, compatibilidad y ausencia de N+1 antes de cualquier publicación.

**Comandos:**

```bash
cd /home/capw/scripts/session-stats
python3 -m py_compile stats_common.py stats-web/main.py stats-web/tests/test_cache_ratio.py
/usr/bin/python3 -m py_compile stats_common.py stats-web/main.py stats-web/tests/test_cache_ratio.py
python3 -m unittest discover -s stats-web/tests -p 'test_cache_ratio.py' -v
python3 -m unittest discover -s stats-web/tests -v
node --test stats-web/tests/costos-logic.test.js
git diff --check
```

Verificación funcional read-only:

- Ejecutar `recalculate_historical_cost()` y registrar ratio nuevo junto con input/output/cache/costo totales.
- Crear un fixture SQLite temporal con sesiones persistidas y `model_usage` para probar los endpoints sin usar `session_history.db` real. Antes de importar `stats-web/main.py`, redirigir `stats_common.DB_PATH` al fixture; después verificar que `main.DB_PATH` apunta al mismo archivo. Sustituir en el módulo importado `recalculate_historical_cost` y cualquier lector externo requerido por el endpoint para impedir acceso a fuentes reales. Afirmar al final que la DB real no cambió.
- Afirmar por endpoint las invariantes correctas: `summary`, `today-summary`, `top-models` y `top-models-30d` conservan tokens, costos, requests, ranking y series; `/api/cache-ratio` puede cambiar sus contadores derivados (`cached`, `uncached`, `input_tokens`, `cache_tokens`) de forma coherente, pero conserva forma, umbral de 1M y ordenamiento.
- Incluir en el fixture: requests globales de sesión distintos de la suma de `model_usage.requests`, sesión mixta con un modelo sobre `5%` pero agregado bajo `5%`, hit+miss elegible, hit inelegible, denominador cero, cache-write-only y mezcla legacy/read-write.
- Probar `recalculate_historical_cost()` con `historical_total`, `legacy_price_adjustment`, `kilocode_legacy` y una representación de fuente externa no persistida; comprobar que los sintéticos no entren al ratio y que las externas se evalúen una vez.
- Importar `stats-web/main.py` con `/usr/bin/python3` y consultar directamente las funciones de resumen si el entorno permite sus dependencias.
- Si el servicio se reinicia en una fase posterior autorizada, probar también:
  - `/healthz`;
  - `/api/summary`;
  - `/api/today-summary?range=today`;
  - `/api/top-models-30d`;
  - `/api/top-models`;
  - `/api/cache-ratio`.
- Instrumentar o inspeccionar las consultas nuevas para confirmar que no existe SQL dentro de loops de sesiones. La elegibilidad del dashboard debe usar un número fijo de consultas respecto de la cantidad de sesiones. No atribuir esa propiedad a todo `recalculate_historical_cost()`, porque los lectores externos ya tienen I/O por sesión fuera de este alcance.
- Revisar `git status --short`, `git diff --stat`, `git diff --check` y el diff completo de los archivos del alcance. Confirmar que `model_aliases.json`, `model_costs.json` y `session_history.db` no fueron tocados por el corte.

**No declarar producción actualizada:** este plan termina con código local verificado. Reinicio, commit, push y publicación requieren una autorización separada y el flujo documentado `private/main` → `sync-public.sh`.

---

## Riesgos y decisiones

1. **Ratio más optimista:** se acepta como consecuencia del filtro. Debe mostrarse/documentarse como ratio de sesiones elegibles.
2. **Sesiones mixtas:** pueden descartar cache válido de un modelo junto con el modelo que causó el ratio bajo. Es intencional y aprobado por el dueño.
3. **Sesiones activas:** la elegibilidad se recalcula en cada consulta; no se persiste.
4. **Datos legacy:** `effective_cache_read_tokens()` mantiene fallback de `cache_tokens`; no se corrige retroactivamente la DB.
5. **Consumo vs ratio:** todo acumulador de tokens/costos/requests debe permanecer en el camino sin filtro; solo los acumuladores de ratio usan elegibilidad.
6. **N+1:** la elegibilidad y los endpoints deben usar consultas con `JOIN`/resultsets completos y mapas en memoria. No usar `SELECT ... WHERE id=?` dentro de loops. Las consultas por sesión ya existentes en los lectores OpenCode/Hermes quedan documentadas como deuda fuera de alcance; no deben presentarse como resueltas por este parche.
7. **Worktree sucio:** hay cambios previos ajenos al ratio; no hacer `reset`, `checkout -f` ni `git rm` para “limpiar”. Respaldar y delimitar el patch.

## Definition of Done

- [ ] La regla `requests < 5 OR ratio >= 5%` tiene tests focales RED→GREEN.
- [ ] Sesiones multi-modelo se filtran como unidad.
- [ ] Histórico/CLI, summary, today-summary, top-models y cache-ratio usan la misma regla.
- [ ] Ratios por modelo usan solo filas de sesiones elegibles.
- [ ] Tokens, costos, requests y DB permanecen sin cambios.
- [ ] No hay resolución de provider ni N+1 nuevo en la elegibilidad/los endpoints; las consultas por sesión preexistentes de lectores externos quedan fuera de alcance y documentadas.
- [ ] Tests Python/Node, compilación y `git diff --check` pasan.
- [ ] README actualizado.
- [ ] No se reinició ni publicó nada sin autorización separada.
