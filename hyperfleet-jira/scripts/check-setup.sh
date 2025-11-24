#!/bin/bash
# HyperFleet JIRA Plugin - Setup Checker
# Verifies jira-cli is installed and configured correctly

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== HyperFleet JIRA Plugin Setup Check ==="
echo ""

# Check if jira-cli is installed
if command -v jira &> /dev/null; then
    echo -e "${GREEN}✓${NC} jira-cli is installed"
    echo "  Version: $(jira version 2>/dev/null || echo 'unknown')"
else
    echo -e "${RED}✗${NC} jira-cli is not installed"
    echo ""
    echo "Install jira-cli:"
    echo "  macOS:  brew install ankitpokhrel/jira-cli/jira-cli"
    echo "  Linux:  See https://github.com/ankitpokhrel/jira-cli#installation"
    exit 1
fi

echo ""

# Check if JIRA_API_TOKEN is set
if [ -n "$JIRA_API_TOKEN" ]; then
    echo -e "${GREEN}✓${NC} JIRA_API_TOKEN is set"
else
    echo -e "${YELLOW}!${NC} JIRA_API_TOKEN environment variable not set"
    echo "  You may need to set this or use .netrc for authentication"
fi

echo ""

# Check if jira-cli is configured
CONFIG_FILE="$HOME/.config/.jira/.config.yml"
if [ -f "$CONFIG_FILE" ] || [ -f "$HOME/.jira/.config.yml" ]; then
    echo -e "${GREEN}✓${NC} jira-cli configuration found"
else
    echo -e "${YELLOW}!${NC} jira-cli configuration not found"
    echo "  Run 'jira init' to configure"
fi

echo ""

# Test connection
echo "Testing JIRA connection..."
if jira me &> /dev/null; then
    CURRENT_USER=$(jira me 2>/dev/null)
    echo -e "${GREEN}✓${NC} Connected to JIRA as: $CURRENT_USER"
else
    echo -e "${RED}✗${NC} Could not connect to JIRA"
    echo "  Run 'jira init' to configure your connection"
    exit 1
fi

echo ""

# Test issue listing
echo "Testing issue access..."
if jira issue list --plain 2>/dev/null | head -1 > /dev/null; then
    echo -e "${GREEN}✓${NC} Can access JIRA issues"
else
    echo -e "${YELLOW}!${NC} Could not list issues (may need project access)"
fi

echo ""

# Test sprint access
echo "Testing sprint access..."
if jira sprint list --plain 2>/dev/null | head -1 > /dev/null; then
    echo -e "${GREEN}✓${NC} Can access sprints"
else
    echo -e "${YELLOW}!${NC} Could not list sprints (Scrum board may not be configured)"
fi

echo ""
echo "=== Setup check complete ==="
echo ""
echo "If all checks passed, you're ready to use the HyperFleet JIRA plugin!"
echo "Try: /my-sprint or /my-tasks"
