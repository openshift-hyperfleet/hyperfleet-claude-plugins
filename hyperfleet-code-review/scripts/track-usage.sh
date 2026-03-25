#!/bin/bash
# HyperFleet Plugin Usage Tracker
# Called from SKILL.md dynamic context during skill loading.
# Sends usage data via GitHub repository_dispatch events.
# Only public information is collected (GitHub username).
#
# Opt-in: on first use, the skill will ask the user for consent.
#         Consent is stored in ~/.claude/.hyperfleet-tracking-consent
# Rate limit: invocation events are sent at most once per day per plugin/skill

CONSENT_FILE="$HOME/.claude/.hyperfleet-tracking-consent"
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

# --- Opt-in consent check ---
if [ -f "$CONSENT_FILE" ] && [ "$(cat "$CONSENT_FILE" 2>/dev/null)" != "yes" ]; then
  exit 0
elif [ ! -f "$CONSENT_FILE" ]; then
  echo "TRACKING_CONSENT_NEEDED"
  echo "TRACKING_CMD: SKILL_NAME=${SKILL_NAME:-unknown} \"$SCRIPT_PATH\""
  exit 0
fi

# Derive plugin info from plugin.json (works in both repo and installed structures)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_JSON=""
for candidate in "$SCRIPT_DIR/../.claude-plugin/plugin.json" "$SCRIPT_DIR/../../.claude-plugin/plugin.json"; do
  [ -f "$candidate" ] && PLUGIN_JSON="$candidate" && break
done

if [ -n "$PLUGIN_JSON" ]; then
  PLUGIN_NAME=$(sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$PLUGIN_JSON" | head -1)
  PLUGIN_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$PLUGIN_JSON" | head -1)
else
  PLUGIN_NAME="unknown"
  PLUGIN_VERSION="unknown"
fi

# Skill name is passed as env var from the dynamic context line
SKILL_NAME="${SKILL_NAME:-unknown}"

# Get GitHub username (cached with 7-day TTL; requires gh CLI)
USERNAME_CACHE="$HOME/.claude/.hyperfleet-gh-username"
CACHE_MAX_AGE=604800  # 7 days in seconds
CACHE_VALID=false
if [ -f "$USERNAME_CACHE" ]; then
  CACHE_AGE=$(( $(date +%s) - $(stat -f %m "$USERNAME_CACHE" 2>/dev/null || stat -c %Y "$USERNAME_CACHE" 2>/dev/null || echo 0) ))
  [ "$CACHE_AGE" -lt "$CACHE_MAX_AGE" ] && CACHE_VALID=true
fi

if [ "$CACHE_VALID" = true ]; then
  USERNAME=$(cat "$USERNAME_CACHE")
elif command -v gh >/dev/null 2>&1; then
  USERNAME=$(gh api user -q '.login' 2>/dev/null || echo "unknown")
  if [ "$USERNAME" != "unknown" ]; then
    mkdir -p "$HOME/.claude"
    echo "$USERNAME" > "$USERNAME_CACHE"
  fi
else
  USERNAME="unknown"
fi

# Bail out early if gh CLI is not available
command -v gh >/dev/null 2>&1 || exit 0

# Detect installation, update, or invocation via marker file that stores version
MARKER="$HOME/.claude/.hyperfleet-${PLUGIN_NAME}-registered"
if [ ! -f "$MARKER" ]; then
  EVENT="installation"
elif [ "$(cat "$MARKER" 2>/dev/null)" != "$PLUGIN_VERSION" ]; then
  EVENT="update"
else
  EVENT="invocation"
fi

# --- Rate limit: invocation events at most once per day per plugin/skill ---
if [ "$EVENT" = "invocation" ]; then
  TODAY=$(date +%Y-%m-%d)
  DAILY_MARKER="$HOME/.claude/.hyperfleet-daily-${PLUGIN_NAME}-${SKILL_NAME}"
  if [ -f "$DAILY_MARKER" ] && [ "$(cat "$DAILY_MARKER" 2>/dev/null)" = "$TODAY" ]; then
    exit 0
  fi
fi

# Send event via GitHub repository_dispatch (synchronous — only persist markers on success)
if gh api repos/openshift-hyperfleet/hyperfleet-claude-plugins/dispatches \
  -f event_type=plugin_usage \
  -f "client_payload[user]=$USERNAME" \
  -f "client_payload[plugin]=$PLUGIN_NAME" \
  -f "client_payload[skill]=$SKILL_NAME" \
  -f "client_payload[event]=$EVENT" 2>/dev/null; then
  mkdir -p "$HOME/.claude"
  if [ "$EVENT" = "installation" ] || [ "$EVENT" = "update" ]; then
    echo "$PLUGIN_VERSION" > "$MARKER"
  elif [ "$EVENT" = "invocation" ]; then
    echo "$TODAY" > "$DAILY_MARKER"
  fi
fi
