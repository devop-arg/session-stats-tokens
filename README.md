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
```

## Usage

```bash
session-stats              # Current session stats (auto-detects tool)
session-stats --capture-all # Persist ALL sessions from all sources
session-stats-history       # Full historical summary
session-stats-period day    # Today
session-stats-period week   # Last 7 days
session-stats-period month  # Last 30 days
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
| `stats_common.py` | Shared module: model costs, DB readers, cost calculation |
| `session_history.json` | Persistent history (auto-maintained, not tracked) |

## Data Sources

| Tool | Path | Format |
|------|------|--------|
| Kilo | `~/.local/share/kilo/kilo.db` | SQLite |
| OpenCode | `~/.local/share/opencode/opencode.db` | SQLite (v1.3.0+) |
| OpenCode | `~/.local/share/opencode/storage/message/` | JSON (v1.1.x fallback) |
| Codex | `~/.codex/sessions/**/*.jsonl` | JSONL |
| Hermes | `~/.hermes/state.db` | SQLite |

## Model Pricing

Costs per 1M tokens (USD). Some models include cache pricing.

| Model | Input | Output | Cache |
|-------|-------|--------|-------|
| Claude Opus 4.5/4.6 | $5.00 | $25.00 | — |
| Claude Sonnet 4.5 | $3.00 | $15.00 | — |
| Claude Haiku 4.5 | $1.00 | $5.00 | — |
| Gemini 3 Pro | $2.00 | $12.00 | — |
| Gemini 3 Flash | $0.50 | $3.00 | — |
| GPT 5.2/5.3/5.4 Codex | $1.75 | $14.00 | — |
| GPT 5 Mini | $0.25 | $2.00 | — |
| GLM-4.7 | $0.39 | $1.75 | $0.19 |
| GLM-5 | $0.80 | $2.56 | $0.16 |
| Kimi K2.5 | $0.50 | $2.60 | $0.09 |
| Minimax M2.1 | $0.27 | $0.95 | — |
| Minimax M2.5 | $0.30 | $1.20 | $0.03 |
| Grok 4.1 Fast | $0.20 | $0.50 | $0.05 |
| DeepSeek V4 Pro | $0.53 | $2.19 | — |
| DeepSeek V4 Flash | $0.14 | $0.60 | — |

**Note:** Cache tokens are added to input for cost calculation.

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
