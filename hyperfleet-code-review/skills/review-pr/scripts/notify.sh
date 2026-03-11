#!/bin/bash
# Cross-platform notification script
# Note: OSC escape sequences and /dev/tty are not available from Claude Code's
# Bash tool, so we use native notification commands only.
TITLE="${1:-Review PR}"
MESSAGE="${2:-Done}"

if command -v osascript &>/dev/null; then
  osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\"" 2>/dev/null &
elif command -v notify-send &>/dev/null; then
  notify-send "$TITLE" "$MESSAGE" 2>/dev/null &
fi
