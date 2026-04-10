#!/bin/bash
# ==========================================
# SearXNG MCP Server - Config Editor (Mac/Linux)
# ==========================================

CONFIG_DIR="$HOME/.searxng-mcp"
CONFIG_FILE="$CONFIG_DIR/.env"

echo ""
echo "=========================================="
echo " SearXNG MCP Server - Configuration"
echo "=========================================="
echo ""

if [ ! -d "$CONFIG_DIR" ]; then
    echo "[Error] Config directory not found: $CONFIG_DIR"
    echo ""
    echo "Please run the following command first:"
    echo "  npm install @otbossam/searxng-mcp-server"
    echo ""
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[Error] Config file not found: $CONFIG_FILE"
    echo ""
    echo "Please run the following command first:"
    echo "  npm install @otbossam/searxng-mcp-server"
    echo ""
    exit 1
fi

echo "Config file: $CONFIG_FILE"
echo ""

# Detect available editor
if [ -n "$EDITOR" ]; then
    EDITOR_CMD="$EDITOR"
elif command -v nano &> /dev/null; then
    EDITOR_CMD="nano"
elif command -v vim &> /dev/null; then
    EDITOR_CMD="vim"
elif command -v vi &> /dev/null; then
    EDITOR_CMD="vi"
else
    # Fallback: just show the file
    echo "[Warning] No text editor found (nano, vim, vi)."
    echo "Showing current config:"
    echo ""
    cat "$CONFIG_FILE"
    echo ""
    echo "To edit manually:"
    echo "  nano $CONFIG_FILE"
    echo ""
    exit 0
fi

echo "Opening with: $EDITOR_CMD"
echo ""

# Open editor
$EDITOR_CMD "$CONFIG_FILE"

echo ""
echo "=========================================="
echo " Settings Saved!"
echo "=========================================="
echo ""
echo "To apply your changes, restart the server:"
echo "  npx -y @otbossam/searxng-mcp-server"
echo ""
echo "Note: Docker container restart is NOT required."
echo "      Changes are applied when Python server starts."
echo ""
