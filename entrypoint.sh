#!/bin/bash
set -e

# Verify Claude Code is accessible
echo "🔍 Checking Claude Code..."
if command -v claude &> /dev/null; then
    echo "✅ Claude Code installed at: $(which claude)"
else
    echo "❌ Claude Code not found in PATH"
    exit 1
fi

# Verify Kimi Code API is configured
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY not set. Kimi Code will not work."
else
    echo "🤖 Kimi Code API configured: $ANTHROPIC_BASE_URL"
fi

# Run the main command
exec "$@"
