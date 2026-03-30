# Activity Types (Sankey Capacity Allocation)

Activity Type is **required** for sprint/kanban capacity planning. Tickets without an Activity Type appear as "Uncategorized" and cannot be properly allocated.

Set via CLI: `--custom activity-type="<value>"`

## Assignment Flow

Evaluate top-down, first match wins:

**Tier 1 — Non-Negotiable (SLAs, Escalations, CVEs):**
- `Associate Wellness & Development` - Onboarding, team growth, training, associate experience
- `Incidents & Support` - Customer escalations, production incidents
- `Security & Compliance` - CVEs, vulnerabilities, security patches

**Tier 2 — Core Principles (Reduce bug backlog, ensure quality):**
- `Quality / Stability / Reliability` - Bugs, SLOs, chores, tech debt, PMR action items, toil reduction

**Tier 3 — Balance remaining capacity for long-term success:**
- `Future Sustainability` - Productivity improvements, upstream contributions, proactive architecture, enablement
- `Product / Portfolio Work` - Strategic portfolio/product work, BU product work, new features

## Decision Flow

1. Is it an escalation, incident, CVE, or training/onboarding? → **Tier 1** (Non-Negotiable)
2. Does it fix bugs, reduce tech debt, improve SLOs, or reduce toil? → **Tier 2** (Quality/Stability/Reliability)
3. Otherwise → **Tier 3**: Is it proactive improvement/enablement? → `Future Sustainability`. Is it new product value? → `Product / Portfolio Work`
