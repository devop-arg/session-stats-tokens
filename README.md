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
git clone https://github.com/weiro2020/session-stats-tokens.git
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

## Files

| File | Description |
|------|-------------|
| `session-stats` | Main script: current session + `--capture-all` |
| `session-stats-history` | Full historical summary |
| `session-stats-period` | Filter by day/week/month |
| `session-stats-models` | Interactive model/price/alias manager |
| `stats_common.py` | Shared module: model costs, DB readers, cost calculation |
| `session_history.json` | Persistent history (auto-maintained, not tracked) |
| `model_costs.json` | Model prices (managed by `session-stats-models`) |
| `model_aliases.json` | Model name aliases (managed by `session-stats-models`) |

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
