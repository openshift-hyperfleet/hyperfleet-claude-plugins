#!/bin/bash
# Cross-platform notification script
# Sends OSC escape sequences (works in most modern terminals) + native fallback
TITLE="${1:-Review PR}"
MESSAGE="${2:-Done}"

# Terminal bell
printf '\a'

# OSC 9 — iTerm2, Windows Terminal, ConEmu
printf '\033]9;%s: %s\a' "$TITLE" "$MESSAGE"

# OSC 777 — Ghostty, urxvt, foot, VSCode (with extension)
printf '\033]777;notify;%s;%s\a' "$TITLE" "$MESSAGE"

# OSC 99 — Kitty
printf '\033]99;;%s: %s\033\\' "$TITLE" "$MESSAGE"

# Native fallback (best-effort, for terminals that don't support OSC)
if command -v osascript &>/dev/null; then
  osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\"" 2>/dev/null &
elif command -v notify-send &>/dev/null; then
  notify-send "$TITLE" "$MESSAGE" 2>/dev/null &
fi
