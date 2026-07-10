# Session Stats Tokens

Track token usage and estimated costs across Kilo, OpenCode, Codex, and Hermes sessions.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **Multi-tool**: Reads from Kilo (SQLite), OpenCode (SQLite), Codex (JSONL), and Hermes (SQLite)
- **Auto-detection**: Finds the most recently active session across all tools
- **Token tracking**: Input, output, cache, and reasoning tokens per model
- **Cost estimation**: Based on hardcoded per-model pricing ($/1M tokens)
- **Persistent history**: Sessions saved to `session_history.json`, survives chat deletion
- **Auto-capture**: Cron-ready `--capture-all` mode for background persistence

## Requirements

- **Python** 3.8+ with `sqlite3`

## Installation

```bash
git clone https://github.com/devop-arg/session-stats-tokens.git
cd session-stats-tokens
chmod +x session-stats session-stats-history session-stats-period

# Add to PATH
mkdir -p ~/.local/bin
ln -sf "$(pwd)/session-stats" ~/.local/bin/session-stats
ln -sf "$(pwd)/session-stats-history" ~/.local/bin/session-stats-history
ln -sf "$(pwd)/session-stats-period" ~/.local/bin/session-stats-period
ln -sf "$(pwd)/session-stats-models" ~/.local/bin/session-stats-models
```

## Usage

```bash
session-stats              # Current session stats (auto-detects tool)
session-stats --capture-all # Persist ALL sessions from all sources
session-stats-history       # Full historical summary
session-stats-period day    # Today
session-stats-period week   # Last 7 days
session-stats-models        # Interactive model/price manager
```

### Sample Output

```
📊 Current Session [OpenCode] (Buscar script tokens opencode): 62 req | In: 193.8K | Out: 14.7K
   └─ ds-v4-flash: 62 req, in:3.1M (cache:2.9M), out:14.7K, cost:$0.1137

💰 Session Cost: $0.1137 - Historical Total (371 sessions): $1261.44
```

### Cron Auto-Capture (Recommended)

Prevents data loss when chat sessions are deleted:

```cron
*/5 * * * * /path/to/session-stats --capture-all >> /path/to/capture.log 2>&1
0 0 * * * rm -f /path/to/capture.log
```

### Data Backup (Automático)

- **Cada 5 min**: `session-stats --capture-all` persiste sesiones a `session_history.db` y `session_history.json`
- **Diario 6 AM**: backup SQLite con rotación de 7 días en `db_backups/`
- Cron configurado localmente, no trackeado en el repo

### Consistencia de capturas por modelo

- **Codex**: las sesiones se actualizan en cada ejecución de
  `--capture-all`. Sus contadores crecen de forma monotónica, por lo que una
  captura temprana no congela el uso de una sesión todavía activa.
- **OpenCode y Kilo**: el desglose se reconstruye desde todos los mensajes de
  la sesión, conservando los tokens y requests de cada modelo usado. Sólo se
  eliminan filas de modelos residuales si los totales reconstruidos coinciden
  exactamente con los de la sesión persistida; ante cualquier diferencia se
  preservan los datos históricos.
- **Hermes** registra un modelo por sesión. **Cursor** conserva el desglose que
  expone su hook local, pero no se depura automáticamente porque esos eventos
  pueden no contener el historial completo.
- **Grok CLI** no expone tokens reales locales: `totalTokens` se usa como
  estimación de contexto y se reparte con una heurística 85/15. Sus tokens y
  costos son orientativos, no adecuados para comparaciones precisas.

### SQLite Schema Migrations

`session-stats` and the web dashboard call `init_db()` on startup. This creates
missing tables and applies non-destructive schema migrations, including the
`cache_read_tokens` and `cache_write_tokens` columns used to separate cache
reads from cache writes.

If a restored or old `session_history.db` fails with `no such column:
cache_read_tokens`, run:

```bash
python3 -c 'import stats_common; stats_common.init_db()'
session-stats --capture-all
```

### Cache Ratios en la Web

El dashboard muestra dos métricas de cache con alcances distintos:

- **Cache Ratio** del encabezado: ratio global histórico calculado con todas las
  sesiones y la semántica de cache de cada fuente.
- **Proporción de cache — modelos con cache**: ratio sólo sobre modelos/filas que
  tuvieron `cache_read_tokens > 0`; sirve para comparar qué modelos aprovechan
  más cache y puede ser mayor que el ratio global.

En la tabla **Uso diario de modelos y costos**, cada modelo muestra `Cache`,
`Ratio`, `Total` y `Costo`. El `Ratio` diario usa el mismo denominador semántico:
si la fuente ya incluye cache en input no duplica esos tokens; si no lo incluye,
usa input efectivo más cache read.

## Repository Strategy

Este proyecto mantiene **dos remotos** con contenido diferente:

| Remote | URL | Branch | Contenido |
|--------|-----|--------|-----------|
| `private` | `github.com:devop-arg/session-stats-tokens-private.git` | `main` | **Canónico**: scripts + datos de sesión (JSON, DB, backups) |
| `origin` | `github.com:devop-arg/session-stats-tokens.git` (público) | `public` | **Sanitizado**: solo scripts, sin datos de usuario |

### Reglas

1. **Trabajar siempre en `main`** (local). `main` trackea `private/main`.
2. **Commitear y pushear al privado** como respaldo:
   ```bash
   git push private main
   ```
3. **Sincronizar al público** con `sync-public.sh`:
   ```bash
   ./sync-public.sh
   ```
   Esto mergea `main` a `public`, excluye datos sensibles y pushea a `origin/public`.

### ¿Qué se excluye del público?

Los siguientes archivos están en `.gitignore` del branch `public`:
- `session_history.json` — historial con nombres de sesiones, costos, tokens
- `session_history.db` — misma información en SQLite
- `codex_sub_costs.json` — costos locales de suscripción Codex
- `db_backups/` — backups de la DB
- `capture.log` — log de capturas

En el branch `main` (privado) estos archivos **sí** están trackeados para backup.

### Commit Hygiene

- **Idioma**: español (consistente con el proyecto)
- **Formato**: `tipo: mensaje imperativo` — ej: `fix: corregir hermes priority`, `feat: agregar dashboard`, `docs: actualizar README`
- **Tipos**: `fix:`, `feat:`, `docs:`, `chore:`, `refactor:`
- **Sin datos sensibles**: no incluir nombres de sesiones, proyectos del usuario, costos específicos ni rutas locales en los mensajes de commit (se pushean al repo público)
- **Antes de pushear al público**: revisar el diff del commit con `git diff --cached` para confirmar que no hay secretos

## Files

| File | Description | Trackeado |
|------|-------------|:---------:|
| `session-stats` | Main script: current session + `--capture-all` | ✅ ambos |
| `session-stats-history` | Full historical summary | ✅ ambos |
| `session-stats-period` | Filter by day/week/month | ✅ ambos |
| `session-stats-models` | Interactive model/price/alias manager | ✅ ambos |
| `stats_common.py` | Shared module: model costs, DB readers, cost calculation | ✅ ambos |
| `model_costs.json` | Model prices (managed by `session-stats-models`) | ✅ ambos |
| `model_aliases.json` | Model name aliases (managed by `session-stats-models`) | ✅ ambos |
| `session_history.json` | Persistent history con nombres, costos, tokens | ✅ privado ❌ público |
| `session_history.db` | Historial en SQLite | ✅ privado ❌ público |
| `codex_sub_costs.json` | Costos locales de suscripción Codex | ✅ privado ❌ público |
| `db_backups/` | Backups diarios de la DB (rotación 7 días) | ✅ privado ❌ público |
| `capture.log` | Log de capturas cron | ❌ ninguno |

## Data Sources

| Tool | Path | Format |
|------|------|--------|
| Kilo | `~/.local/share/kilo/kilo.db` | SQLite |
| OpenCode | `~/.local/share/opencode/opencode.db` | SQLite (v1.3.0+) |
| OpenCode | `~/.local/share/opencode/storage/message/` | JSON (v1.1.x fallback) |
| Codex | `~/.codex/sessions/**/*.jsonl` | JSONL |
| Hermes | `~/.hermes/state.db` | SQLite |
| Cursor | `~/.cursor/usage-events.jsonl` | JSONL (hook local) |
| Grok CLI | `~/.grok/sessions/**/summary.json` | JSON + estimación de contexto |

## Model Pricing

Costs per 1M tokens (USD). Some models include cache pricing.

- **Auto-seed**: `session-stats --capture-all` siembra automáticamente en
  `model_costs.json` los modelos usados en la DB que aún no tienen precio, con
  `0/0/0` (idempotente). Ya no hace falta darlos de alta a mano.
- **Edición**: la UI web (`/models`) permite editar los precios de los modelos
  ya presentes (input/output/cache). No se pueden crear modelos desde la UI;
  los nuevos aparecen solos vía auto-seed al ser usados.
- **Gestión alternativa**: el CLI `session-stats-models` permite
  agregar/editar/borrar modelos y aliases, y listar huérfanos/sin uso.
  Precios en `model_costs.json`, aliases en `model_aliases.json`.
- **Costos Codex**: `/api/subscription-estimate` agrega automáticamente los
  modelos usados cuyo nombre contiene `gpt` a `codex_sub_costs.json` con costo
  `0` si todavía no existen. El selector de `/costos` los muestra como
  `costo pendiente`; el precio Codex real se carga luego con **Guardar**.
  Actualizar los precios API no modifica `cost_sub`: son valores independientes.

El costo se calcula en `stats_common.calculate_cost` como
`input·price_in + output·price_out + cache_tokens·price_cache` (si el modelo no
registra cache tokens, el término cache es 0 da igual el precio).

### Comparador de costos en Android (`/costos`)

En viewports mobile (`≤768px`), la tabla completa se reemplaza por un comparador
compacto compatible con Chrome y Firefox Android:

- muestra el modelo Codex elegido, los 5 costos efectivos inmediatamente más
  baratos y los 5 inmediatamente más caros;
- compara **Costo por API** contra **Costo efectivo por suscripción**;
- muestra ahorro/multiplicador y el punto de equilibrio en tokens y porcentaje
  de la capacidad estimada;
- conserva la tabla y el ordenamiento completos en desktop.

El `cost_sub` guardado manualmente es la fuente de verdad. Un modelo Codex sin
precio usa `cost_api / 20` únicamente para ubicarlo en la comparación, bajo el
supuesto `$20 de suscripción ≈ $400 de API`. Ese fallback no se persiste y la
interfaz mantiene visible `precio pendiente` hasta que se guarde un valor real.

Pruebas de lógica:

```bash
node --test stats-web/tests/costos-logic.test.js
```

### Siempre muestra Hermes aunque esté cerrado

Si `session-stats` siempre muestra `[Hermes]` incluso después de cerrarlo y ya abriste OpenCode/Kilo, es probable que Hermes haya dejado una sesión abierta (sin `ended_at` en `~/.hermes/state.db`).

Para solucionarlo, cerrar todas las sesiones abiertas de Hermes:

```bash
sqlite3 ~/.hermes/state.db "UPDATE sessions SET ended_at = started_at + 60 WHERE (ended_at IS NULL OR ended_at = 0) AND input_tokens > 0;"
```

Esto ocurre cuando el proceso de Hermes se mata abruptamente (ej: `kill`, crash del sistema, cierre del terminal padre) antes de cerrar la sesión correctamente.

## Troubleshooting

### "No active session found"
- Make sure at least one tool (Kilo, OpenCode, Codex, or Hermes) has an active session with token usage
- Kilo: `~/.local/share/kilo/kilo.db` must exist
- OpenCode: `~/.local/share/opencode/opencode.db` must exist
- Codex: `~/.codex/sessions/` must exist
- Hermes: `~/.hermes/state.db` must exist

### History lost after deleting a chat session
- Set up the cron auto-capture (see above) to persist sessions before deletion
- Run `session-stats --capture-all` to recover any uncaptured sessions

## License

MIT — see [LICENSE](LICENSE)
