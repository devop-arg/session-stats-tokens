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

## Model Pricing

Costs per 1M tokens (USD). Some models include cache pricing. Managed interactively via:

```bash
session-stats-models
```

Features: add/edit/delete models, manage aliases, detect orphan models without pricing, list unused models. Prices stored in `model_costs.json`, aliases in `model_aliases.json`.

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
