# OpenCode/Kilo/Codex Antigravity Stats

Monitor your Antigravity API quotas and track Kilo/OpenCode/Codex session statistics including token usage and estimated costs.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **Quota Monitor**: Check remaining quota for all configured Antigravity accounts
  - Smart Check optimization: only queries active account when quotas are OK
  - Full Sweep: queries all accounts when active is exhausted or on demand
  - 30-second cache to minimize API calls
  - Hybrid token caching with auto-retry on invalid tokens

- **Session Stats**: Track token usage and costs per Kilo/OpenCode/Codex session
   - Lee de tres fuentes: Kilo (SQLite), OpenCode (JSON), Codex (JSONL)
   - Detecta automáticamente qué herramienta se está usando
   - Input/output tokens por modelo
   - Estimated costs based on model pricing
   - Historical tracking across sessions
   - Recálculo unificado desde tokens (consistencia total)

## Requirements

- **Node.js** 18 or higher
- **Python** 3.8 or higher (con módulo `sqlite3` incluido)
- **OpenCode CLI** 1.1.12+ (JSON) o 1.3.0+ (SQLite), **Kilo CLI** 7.0.50+, o **Codex CLI** 0.98.0+

## Installation

### Quick Install

```bash
git clone https://github.com/weiro2020/opencode-antigravity-stats-quota.git
cd opencode-antigravity-stats-quota
./install.sh
```

### Manual Install

1. Clone the repository:
```bash
git clone https://github.com/weiro2020/opencode-antigravity-stats-quota.git
cd opencode-antigravity-stats-quota
```

2. Make scripts executable:
```bash
chmod +x antigravity-quota.js session-stats session-stats-history session-stats-period quota
```

3. Add to your PATH (choose one):
```bash
# Option A: Symlink to ~/.local/bin
mkdir -p ~/.local/bin
ln -sf "$(pwd)/quota" ~/.local/bin/quota

# Option B: Add directory to PATH in ~/.bashrc
echo 'export PATH="$PATH:/path/to/opencode-antigravity-stats-quota"' >> ~/.bashrc
```

## Configuration

### Antigravity Accounts

The quota monitor reads account configuration from `~/.config/opencode/antigravity-accounts.json`, which is automatically created by the `opencode-antigravity-auth` plugin.

Example structure (created by the plugin):
```json
{
  "activeIndex": 0,
  "accounts": [
    {
      "email": "user@example.com",
      "refreshToken": "...",
      "projectId": "..."
    }
  ]
}
```

### Setting Up Antigravity Auth

1. Install the plugin:
```bash
opencode plugin install opencode-antigravity-auth@1.3.1
```

2. Add accounts:
```bash
opencode /antigravity-auth login
```

## Usage

### Combined Dashboard (Recommended)

```bash
quota              # Show quotas + session stats
quota --refresh    # Force refresh quotas
quota --help       # Show help
```

### Individual Commands

```bash
# Quota monitor only
node antigravity-quota.js              # Normal mode with cache
node antigravity-quota.js --compact    # Compact output
node antigravity-quota.js --refresh    # Force refresh
node antigravity-quota.js --json       # JSON output

# Session stats only
./session-stats                        # Current session
./session-stats-history                # All sessions history
./session-stats-period day             # Today's stats
./session-stats-period week            # Last 7 days
./session-stats-period month           # Last 30 days
```

### Sample Output

```
📊 Current Session [Kilo]: 253 req | In: 1.1M | Out: 95.5K
   └─ mimo-v2-pro: 253 req, in:20.6M (cache:19.5M), out:95.5K, cost:$1.36

💰 Session Cost: $1.36 - Historical Total (195 sessions): $915.09
```

### Sample History Output

```
HISTORIAL ACUMULADO (195 sesiones)
   Requests: 11981
   Input:    315.8M tokens
   Output:   5.0M tokens

DESGLOSE POR MODELO:
   claude-opus-4.5: 3896 req, in:98.1M, out:1.9M, costo:$538.00
   gpt-5.4: 167 req, in:135.5M (cache:66.0M), out:471.9K, costo:$128.30
   gpt-5.3-codex: 73 req, in:77.3M (cache:37.2M), out:161.2K, costo:$72.35
   ...
```

## OpenCode Integration

Add this to your OpenCode instructions file (`~/.config/opencode/instructions.md`) to automatically show stats:

```markdown
## Stats & Quotas
At the end of each response, run the `quota` command if more than 5 seconds 
have passed since the last execution (to avoid loops).
```

## Files Reference

| File | Description |
|------|-------------|
| `antigravity-quota.js` | Node.js script for API quota monitoring |
| `session-stats` | Python script for session token tracking |
| `session-stats-history` | View all historical sessions |
| `session-stats-period` | Filter stats by time period |
| `quota` | Unified wrapper script |
| `migrate.py` | Migration tool for old history format |

## Cache Files (Not Tracked)

These files are created in `~/.config/opencode/` and contain sensitive data:

| File | Description |
|------|-------------|
| `antigravity-accounts.json` | Account credentials (created by auth plugin) |
| `antigravity-tokens.json` | Cached OAuth2 access tokens |
| `antigravity-quota-cache.json` | Cached quota results (30s TTL) |

## Model Pricing

Costos estimados por 1M tokens (USD). Algunos modelos tienen precios de caché especiales.

| Model | Input | Output | Cache |
|-------|-------|--------|-------|
| Claude Opus 4.5/4.6 | $5.00 | $25.00 | - |
| Claude Sonnet 4.5 | $3.00 | $15.00 | - |
| Claude Haiku 4.5 | $1.00 | $5.00 | - |
| Gemini 3 Pro | $2.00 | $12.00 | - |
| Gemini 3 Flash | $0.50 | $3.00 | - |
| GPT 5.2 Codex | $1.75 | $14.00 | - |
| GPT 5.2 | $1.75 | $14.00 | - |
| Codex Max | $1.25 | $10.00 | - |
| GPT 5 Mini | $0.25 | $2.00 | - |
| GLM-4.7 Free | $0.43 | $2.20 | - |
| GLM-5 | $0.80 | $2.56 | $0.16 |
| Step 3.5 Flash | $0.10 | $0.30 | - |
| Kimi K2.5 | $0.50 | $2.60 | $0.09 |
| Minimax M2.1 | $0.27 | $0.95 | - |
| Minimax M2.5 | $0.30 | $1.20 | $0.03 |
| Trinity Large Preview | $0.25 | $1.00 | - |
| Grok 4.1 Fast | $0.20 | $0.50 | $0.05 |

**Nota:** Los tokens de caché (cache.read) se suman al input para el cálculo de costos.

## Troubleshooting

### "No session found"
- Make sure Kilo, OpenCode, or Codex is running and has an active session
- Kilo: `~/.local/share/kilo/kilo.db` debe existir
- OpenCode: `~/.local/share/opencode/storage/message/` debe existir
- Codex: `~/.codex/sessions/` debe existir

### "Could not read accounts file"
- Run `opencode /antigravity-auth login` to set up accounts
- Verify `~/.config/opencode/antigravity-accounts.json` exists

### Token errors (401/403)
- The script automatically invalidates and regenerates tokens
- If persistent, try `node antigravity-quota.js --refresh`

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- Based on concepts from [opencode-antigravity-quota](https://github.com/frieser/opencode-antigravity-quota) by frieser
- Developed for use with [OpenCode CLI](https://opencode.ai)

## Changelog

### 2026-02-12 - Cache Tokens Support

**Problema resuelto:** Los tokens de caché (`cache.read`) no se estaban incluyendo en los cálculos de tokens ni en los costos.

**Cambios realizados:**

1. **session-stats** (`session-stats`)
   - Ahora extrae y suma `tokens.cache.read` al total de input
   - Guarda el campo `cache` por separado para cálculo de costos
   - Muestra los tokens de caché en el output: `in:791.9K (cache:742.0K)`
   - Pasa el parámetro `cache` a `calculate_cost()` para calcular el costo correctamente

2. **session-stats-history** (`session-stats-history`)
   - Soporte completo para tokens de caché en el historial
   - Muestra cache en el desglose por modelo
   - Recalcula costos con cache para todas las sesiones

3. **stats_common.py**
   - Función `calculate_cost()` ahora acepta parámetro `cache_tokens`
   - Calcula: `input_cost + output_cost + cache_cost`
   - MODEL_COSTS actualizado con precios de cache para:
     - `glm-5`: cache $0.16/M
     - `kimi-k2.5`: cache $0.09/M
     - `minimax-m2.5`: cache $0.03/M
   - MODEL_ALIASES actualizado:
     - `minimax-m2.5-free` → `minimax-m2.5`
     - `minimax-m2.5` → `minimax-m2.5`
   - Fallbacks actualizados para detectar modelos no encontrados en MODEL_COSTS

4. **Precios actualizados:**
   | Model | Input | Output | Cache |
   |-------|-------|--------|-------|
   | GLM-5 | $0.80 | $2.56 | $0.16 |
   | Kimi K2.5 | $0.50 | $2.60 | $0.09 |
   | Minimax M2.5 | $0.30 | $1.20 | $0.03 |
   | Grok 4.1 Fast | $0.20 | $0.50 | $0.05 |

**Nota:** Las sesiones históricas guardadas antes de esta actualización no tienen el campo `cache`, por lo que los costos históricos no incluyen cache. Solo las sesiones nuevas a partir de esta fecha tendrán el cálculo completo.

### 2026-03-23 - Soporte Kilo 7.0.50 + Limpieza

**Problema resuelto:** 
- Kilo 7.0.50 migró a SQLite (`~/.local/share/kilo/kilo.db`) y session-stats no mostraba sus datos.
- Los costos de `session-stats` y `session-stats-history` no coincidían ($7.34 de diferencia).
- Secciones innecesarias (Kilocode CLI legacy, Consultas externas) ensuciaban el output.

**Cambios realizados:**

1. **session-stats** (`session-stats`)
   - Lee de Kilo (SQLite) y OpenCode (JSON), detecta automáticamente la fuente
   - Muestra etiqueta `[Kilo]` o `[OpenCode]` en el encabezado
   - Usa `recalculate_historical_cost()` para cálculo unificado de costos
   - Eliminada sección "Consultas externas"
   - Eliminada sección "Kilocode CLI" (legacy)
   - Funciones nuevas: `get_kilo_sessions()`, `get_session_stats_sqlite()`, `has_real_usage_sqlite()`

2. **session-stats-history** (`session-stats-history`)
   - Usa `recalculate_historical_cost()` compartida (antes calculaba inline)
   - Eliminada sección "CONSULTAS EXTERNAS"
   - Eliminada sección "KILOCODE CLI"
   - Output limpio: solo historial + desglose por modelo

3. **stats_common.py**
   - Nueva función `recalculate_historical_cost(history_file)` compartida
   - Recalcula costos desde tokens con la lógica actual (siempre consistente)
   - Retorna: `total_cost`, `total_sessions`, `total_requests`, `total_input`, `total_output`, `models_totals`

4. **session_history.json**
   - Entrada `kilocode_legacy` agregada con datos de las 7 tareas viejas de Kilocode CLI
   - Preserva tokens y costos legacy en el historial sin mostrar sección aparte

5. **Fuentes de datos**

   | Fuente | Ruta | Método |
   |--------|------|--------|
   | Kilo | `~/.local/share/kilo/kilo.db` | SQLite (tabla `message`) |
   | OpenCode | `~/.local/share/opencode/opencode.db` | SQLite (v1.3.0+) |
   | OpenCode | `~/.local/share/opencode/storage/message/` | JSON (v1.1.x fallback) |
   | Codex | `~/.codex/sessions/**/*.jsonl` | JSONL (eventos `token_count`) |
   | Historial | `session_history.json` | Recálculo desde tokens |

6. **Totales verificados:** `session-stats` y `session-stats-history` dan exactamente el mismo costo total.

### 2026-03-23 - Soporte Codex CLI (OpenAI)

**Problema resuelto:** Las sesiones de Codex CLI (`@openai/codex`) no se mostraban en session-stats ni en el historial.

**Investigación de datos de Codex:**
- Codex CLI 0.115.0 almacena sesiones en `~/.codex/sessions/2026/**/*.jsonl`
- Cada sesión JSONL contiene eventos `token_count` con desglose completo de tokens
- `state_5.sqlite` tiene tabla `threads` con `tokens_used` (no desglosado, se usa JSONL)
- Modelos usados: `gpt-5.3-codex` (15 sesiones feb 2026), `gpt-5.4` (3 sesiones mar 2026)

**Cambios realizados:**

1. **stats_common.py**
   - Nuevas funciones: `get_codex_sessions()`, `has_real_usage_codex()`, `get_codex_session_stats()`
   - `recalculate_historical_cost()` ahora incluye sesiones de Codex desde JSONL
   - Evita doble conteo: sesiones Codex ya guardadas en `session_history.json` se saltan
   - `gpt-5.3-codex` agregado a `MODEL_COSTS` ($1.75/$14) y `MODEL_ALIASES`

2. **session-stats** (`session-stats`)
   - `get_current_session()` ahora detecta Codex (JSONL) además de Kilo y OpenCode
   - Etiqueta `[Codex]` en el encabezado cuando la sesión activa es de Codex
   - Extrae stats de `token_count` events (input_tokens, cached_input_tokens, output_tokens, reasoning_output_tokens)

3. **session-stats-history** (`session-stats-history`)
   - El total histórico ahora incluye sesiones de Codex automáticamente (18 sesiones, ~$199.68)

4. **Fuentes de datos actualizadas:**

   | Fuente | Ruta | Método |
   |--------|------|--------|
   | Kilo | `~/.local/share/kilo/kilo.db` | SQLite (tabla `message`) |
   | OpenCode | `~/.local/share/opencode/opencode.db` | SQLite (v1.3.0+) |
   | OpenCode | `~/.local/share/opencode/storage/message/` | JSON (v1.1.x fallback) |
   | Codex | `~/.codex/sessions/**/*.jsonl` | JSONL (eventos `token_count`) |
   | Historial | `session_history.json` | Recálculo desde tokens |

5. **Totales verificados:** 206 sesiones, $920.73 total (session-stats = session-stats-history)

### 2026-03-23 (b) - Soporte OpenCode 1.3.0 (SQLite)

**Problema resuelto:** OpenCode 1.3.0 migró de JSON a SQLite (`~/.local/share/opencode/opencode.db`). Las sesiones nuevas no aparecían en session-stats porque seguía leyendo los JSON viejos.

**Cambios realizados:**

1. **stats_common.py**
   - Nueva función `get_opencode_sqlite_sessions()` para leer sesiones de OpenCode SQLite
   - `recalculate_historical_cost()` incluye sesiones OpenCode SQLite no guardadas en historial
   - Constante `OPENCODE_DB_PATH`

2. **session-stats** (`session-stats`)
   - `get_opencode_sessions()` intenta SQLite primero (v1.3.0+), fallback a JSON (v1.1.x)
   - `get_session_stats_sqlite()` y `has_real_usage_sqlite()` aceptan `db_path` parametrizable
   - `get_current_session()` maneja `opencode_sqlite` y `opencode_json` como fuentes separadas
   - Muestra título de sesión de OpenCode cuando está disponible

3. **Totales verificados:** 206 sesiones, $920.73 (11 sesiones nuevas de OpenCode SQLite sumadas)
