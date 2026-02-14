#!/bin/bash

# Ensure Cache Architecture Repository Script
# This script ensures the HyperFleet architecture repository exists in cache and is up-to-date

set -e

# ============================================================================
# Configuration
# ============================================================================

CACHE_DIR="$HOME/.claude/plugins/cache/hyperfleet-devtools"
ARCH_REPO="$CACHE_DIR/architecture"

# ============================================================================
# Ensure cache directory exists
# ============================================================================

mkdir -p "$CACHE_DIR"

# ============================================================================
# Check if architecture repo exists in cache
# ============================================================================

if [ ! -d "$ARCH_REPO" ]; then
    echo "📥 Architecture repository not found in cache" >&2
    echo "   Cloning from GitHub..." >&2
    echo "" >&2

    cd "$CACHE_DIR"
    git clone https://github.com/openshift-hyperfleet/architecture.git

    if [ $? -eq 0 ]; then
        echo "✅ Architecture repository cloned to cache" >&2
        echo "   Location: $ARCH_REPO" >&2
    else
        echo "❌ Error: Failed to clone architecture repository" >&2
        echo "" >&2
        echo "This is required for building the knowledge index." >&2
        echo "Please check your network connection and try again." >&2
        exit 1
    fi
else
    echo "🔄 Updating cached architecture repository..." >&2

    cd "$ARCH_REPO"

    # Ensure on main branch
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

    if [ "$CURRENT_BRANCH" != "main" ]; then
        echo "   Switching to main branch..." >&2
        git checkout main 2>&1 || {
            echo "⚠️  Warning: Failed to checkout main branch" >&2
            echo "   Continuing with current branch: $CURRENT_BRANCH" >&2
        }
    fi

    # Pull latest changes
    git pull origin main 2>&1

    if [ $? -eq 0 ]; then
        echo "✅ Architecture repository updated to latest" >&2
    else
        echo "⚠️  Warning: git pull failed" >&2
        echo "   Continuing with current cached version" >&2
    fi
fi

echo "" >&2
echo "Architecture repository ready: $ARCH_REPO" >&2

# Output the path for the caller to use (stdout only)
echo "$ARCH_REPO"
