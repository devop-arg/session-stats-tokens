#!/bin/bash
#
# Install script for OpenCode Antigravity Stats & Quota
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"

echo "Installing OpenCode Antigravity Stats & Quota..."
echo ""

# Check requirements
echo "Checking requirements..."

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18 or higher."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version $NODE_VERSION found, but 18+ is required."
    exit 1
fi
echo "✓ Node.js $(node -v)"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi
echo "✓ Python $(python3 --version | cut -d' ' -f2)"

# Check for OpenCode config
if [ ! -d "$HOME/.config/opencode" ]; then
    echo "⚠ OpenCode config directory not found. Creating..."
    mkdir -p "$HOME/.config/opencode"
fi

# Check for antigravity accounts
if [ ! -f "$HOME/.config/opencode/antigravity-accounts.json" ]; then
    echo ""
    echo "⚠ No Antigravity accounts configured."
    echo "  Run 'opencode /antigravity-auth login' after installation."
fi

echo ""

# Make scripts executable
echo "Making scripts executable..."
chmod +x "$SCRIPT_DIR/antigravity-quota.js"
chmod +x "$SCRIPT_DIR/session-stats"
chmod +x "$SCRIPT_DIR/session-stats-history"
chmod +x "$SCRIPT_DIR/session-stats-period"
chmod +x "$SCRIPT_DIR/quota"
echo "✓ Scripts are executable"

# Create bin directory if needed
if [ ! -d "$BIN_DIR" ]; then
    echo "Creating $BIN_DIR..."
    mkdir -p "$BIN_DIR"
fi

# Create symlink
echo "Creating symlink..."
ln -sf "$SCRIPT_DIR/quota" "$BIN_DIR/quota"
echo "✓ Linked quota -> $SCRIPT_DIR/quota"

# Check if bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠ $BIN_DIR is not in your PATH."
    echo "  Add this line to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "    export PATH=\"\$PATH:$BIN_DIR\""
    echo ""
    echo "  Then run: source ~/.bashrc"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  quota              # Show quotas + session stats"
echo "  quota --refresh    # Force refresh quotas"
echo "  quota --help       # Show help"
echo ""
echo "For OpenCode integration, add to ~/.config/opencode/instructions.md:"
echo ""
echo "  ## Stats & Quotas"
echo "  At the end of each response, run the \`quota\` command."
echo ""
