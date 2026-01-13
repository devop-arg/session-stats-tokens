# OpenCode Antigravity Stats & Quota

Monitor your Antigravity API quotas and track OpenCode session statistics including token usage and estimated costs.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **Quota Monitor**: Check remaining quota for all configured Antigravity accounts
  - Smart Check optimization: only queries active account when quotas are OK
  - Full Sweep: queries all accounts when active is exhausted or on demand
  - 30-second cache to minimize API calls
  - Hybrid token caching with auto-retry on invalid tokens

- **Session Stats**: Track token usage and costs per OpenCode session
  - Input/output tokens per model
  - Estimated costs based on model pricing
  - Historical tracking across sessions

## Requirements

- **Node.js** 18 or higher
- **Python** 3.8 or higher
- **OpenCode CLI** 1.1.12 or higher
- **opencode-antigravity-auth** plugin 1.2.9-beta.1 or higher

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
opencode plugin install opencode-antigravity-auth@1.2.9-beta.1
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
🚀 Smart Check: Updating account1...
[1/1] account1
   ⏳ Token... ✓ cache (45m)
   ⏳ Quotas... ✓ 4 models

☁️  QUOTAS (smart: account1)

### Claude Sonnet 4.5
[██████████] 100%  4h 32m    account1

### Gemini 3 Pro
[████░░░░░░]  42%  2h 15m    account1

📊 Current Session: 15 req | In: 125.3K | Out: 42.1K
   └─ claude-sonnet-4-5: 10 req, in:98.2K, out:35.4K, cost:$0.0421
   └─ gemini-3-flash: 5 req, in:27.1K, out:6.7K, cost:$0.0034

💰 Session Cost: $0.0455 - Historical Total (12 sessions): $0.8234
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

Estimated costs per 1M tokens (USD):

| Model | Input | Output |
|-------|-------|--------|
| Claude Opus 4.5 Thinking | $5.00 | $25.00 |
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| Gemini 3 Pro | $2.00 | $12.00 |
| Gemini 3 Flash | $0.50 | $3.00 |
| GPT 5.2 Codex | $1.75 | $14.00 |
| Codex Max | $1.25 | $10.00 |

## Troubleshooting

### "No session found"
- Make sure OpenCode is running and has an active session
- Check that `~/.local/share/opencode/storage/message/` exists

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
