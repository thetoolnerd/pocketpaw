#!/bin/bash
set -euo pipefail

# Persistent data root (Railway volume mount)
DATA_ROOT="${POCKETPAW_DATA_DIR:-/home/pocketpaw/data}"
PERSIST_PW_DIR="${DATA_ROOT}/.pocketpaw"

# Force a stable HOME so Path.home() resolves to the volume-backed path.
export HOME="${HOME:-$DATA_ROOT}"

mkdir -p "$PERSIST_PW_DIR"

# Ensure both possible home locations point to persistent .pocketpaw.
for BASE in "/root" "/home/pocketpaw"; do
  TARGET="${BASE}/.pocketpaw"
  if [ -L "$TARGET" ]; then
    continue
  fi
  if [ -d "$TARGET" ] && [ ! -e "${TARGET}/.do-not-touch" ]; then
    rm -rf "$TARGET"
  fi
  ln -sfn "$PERSIST_PW_DIR" "$TARGET"
done

# Optional: pin a fixed master token across all redeploys.
if [ -n "${POCKETPAW_MASTER_TOKEN:-}" ]; then
  printf '%s\n' "$POCKETPAW_MASTER_TOKEN" > "${PERSIST_PW_DIR}/access_token"
  chmod 600 "${PERSIST_PW_DIR}/access_token"
fi

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

echo "📁 PocketPaw data dir: ${PERSIST_PW_DIR}"

# Run the main command
exec "$@"
