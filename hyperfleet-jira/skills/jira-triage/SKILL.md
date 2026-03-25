---
name: jira-triage
description: Validates JIRA tickets have required fields and quality standards for sprint planning.
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# JIRA Ticket Triage Skill

## Dynamic context

- tracking: !`SKILL_NAME=jira-triage "${CLAUDE_SKILL_DIR}/../../scripts/track-usage.sh" 2>&1`

## Usage Tracking Consent

If the tracking dynamic context above shows `TRACKING_CONSENT_NEEDED`, you MUST ask the user and **STOP immediately — do NOT proceed with any skill step, do NOT call any tool, do NOT start gathering data**. Output ONLY the consent question and wait for the user's reply:

> "HyperFleet plugins collect usage data to help the team understand adoption. The following fields are sent: your GitHub username, plugin name, skill name, and event type (installation/update/invocation). Would you like to enable usage tracking? (yes/no)"

After the user responds:
- If the user explicitly says "yes": run two separate Bash commands: first `mkdir -p ~/.claude && echo "yes" > ~/.claude/.hyperfleet-tracking-consent` to save consent, then run the exact command shown in the `TRACKING_CMD:` line from the tracking dynamic context output above.
- If the user declines: run `mkdir -p ~/.claude && echo "no" > ~/.claude/.hyperfleet-tracking-consent`
- Then continue executing the skill normally.
- No data is collected until you give consent. Tracking begins only after you agree.
- To change your choice later, delete `~/.claude/.hyperfleet-tracking-consent` and you'll be asked again.

## When to Use This Skill

Activate when the user:
- Asks to "triage" a ticket
- Asks if a ticket is "ready for sprint"
- Wants to validate ticket completeness
- Asks "does this ticket have everything we need?"

## Triage Checklist

### Required Fields (Must Have)
| Field | Requirement |
|-------|-------------|
| Title | Clear, actionable, under 100 characters |
| Description | Detailed context (recommend > 100 characters) |
| Acceptance Criteria | At least 2 clear, testable criteria |
| Story Points | Set (scale: 0, 1, 3, 5, 8, 13) |
| Component | One of: Adapter, API, Architecture, Sentinel |
| Activity Type | Set for capacity planning |

### Recommended Fields
| Field | Requirement |
|-------|-------------|
| Labels | At least 1 relevant label |
| Epic Link | Connected to parent epic (for Stories) |
| Fix Version | Target release identified |
| Priority | Explicitly set (not just default) |

### Quality Checks
- **CRITICAL: Not a duplicate** - Search for similar titles/descriptions in backlog before adding
- No ambiguous language ("maybe", "probably", "TBD", "possibly")
- Technical approach outlined or referenced
- Dependencies identified and linked
- Scope is achievable in one sprint

## Components

Valid components for HYPERFLEET project:
- **Adapter** - Integration adapters
- **API** - API services
- **Architecture** - Architecture decisions and documentation
- **Sentinel** - Background processing services

## How to Check a Ticket

Use jira-cli to fetch ticket details:

```bash
jira issue view TICKET-KEY --plain 2>/dev/null
```

For JSON output with all fields:
```bash
jira issue view TICKET-KEY --raw 2>/dev/null
```

## Output Format

When analyzing a ticket, provide:

### Ticket: TICKET-KEY

**Summary:** [Ticket title]

#### Triage Assessment

| Check | Status | Notes |
|-------|--------|-------|
| Title | PASS/FAIL | [Issue if any] |
| Description | PASS/FAIL | [Length: X chars] |
| Acceptance Criteria | PASS/FAIL | [Count: X criteria] |
| Story Points | PASS/FAIL | [Value or "Missing"] |
| Component | PASS/FAIL | [Must be: Adapter, API, Architecture, or Sentinel] |
| Activity Type | PASS/FAIL | [Type or "Uncategorized"] |

#### Overall Score: X/6 Required Checks Passed

#### Verdict
- **READY FOR SPRINT** - All required fields present, good quality
- **NEEDS MINOR FIXES** - 1-2 issues to address
- **NOT READY** - Multiple critical issues

#### Recommended Actions
1. [Specific action to fix issue 1]
2. [Specific action to fix issue 2]

## Activity Types (Sankey Capacity Allocation)

Activity Type is **required** for sprint/kanban capacity planning. Tickets without an Activity Type appear as "Uncategorized" and cannot be properly allocated.

### Reactive Work (Non-Negotiable First)
| Activity Type | Description | Examples |
|---------------|-------------|----------|
| **Associate Wellness & Development** | Onboarding, team growth, training, associate experience | Training sessions, mentorship |
| **Incidents & Support** | Escalations, production issues | Customer escalations, outages |
| **Security & Compliance** | Vulnerabilities and weaknesses, CVEs | Security patches, compliance fixes |

### Core Principles (Quality Focus)
| Activity Type | Description | Examples |
|---------------|-------------|----------|
| **Quality / Stability / Reliability** | Bugs, SLOs, chores, tech debt, PMR action items, toil reduction | Bug fixes, performance improvements |

### Proactive Work (Balance Remaining Capacity)
| Activity Type | Description | Examples |
|---------------|-------------|----------|
| **Future Sustainability** | Productivity improvements, team improvements, upstream, proactive architecture, enablement | Tooling, automation, refactoring |
| **Product / Portfolio Work** | Strategic portfolio (HATSTRAT), strategic product, product outcome, BU features | New features, product enhancements |

### Priority Order
1. **Non-Negotiable**: Achieve SLAs for Escalations & CVEs
2. **Core Principles**: Reduce bug backlog, ensure quality/stability/reliability
3. **Then Balance**: Set up for long-term success by balancing remaining capacity between Future Sustainability and Product Work

## Red Flags to Highlight

- Descriptions under 50 characters
- "TBD" or placeholder text in any field
- Story points of 13+ (must be broken down)
- No acceptance criteria at all
- Vague titles like "Fix bug" or "Update feature"
- Tickets open > 30 days without progress
- **Missing Activity Type** (appears as Uncategorized in capacity planning)
- **Invalid Component** (must be Adapter, API, Architecture, or Sentinel)

## Integration with Commands

This skill complements the `/triage` command:
- Command: Bulk audit of sprint tickets
- Skill: Deep-dive on individual ticket quality
