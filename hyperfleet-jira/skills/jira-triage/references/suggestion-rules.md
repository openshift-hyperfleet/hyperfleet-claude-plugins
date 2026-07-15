# Suggestion Rules

Rules for suggesting values when required fields are missing or invalid. Valid values for all fields come from **ticket-hygiene.md** (fetched at triage start) — do not hardcode them here.

## Activity Type

When Activity Type is missing, "Uncategorized", or does not match any valid value from ticket-hygiene.md, suggest a replacement based on ticket content. Evaluate top-down using the tier order from ticket-hygiene.md — first match wins.

Keyword hints for matching:
- Incidents, escalations, support, on-call, customer impact → Tier 1
- CVEs, vulnerabilities, compliance, security → Tier 1
- Bugs, SLOs, CI/build chores, tech debt, toil reduction, PMR → Tier 2
- Onboarding, training, conferences → Tier 1
- Proactive architecture, productivity improvements, automation, upstream → Tier 3
- New features, customer-facing functionality, roadmap → Tier 3

Tiebreaker when ambiguous:
- Fixes something existing → quality/stability tier
- Prevents future problems or improves processes → sustainability tier
- Delivers new customer value → product tier

## Component

When Component is missing or invalid (does not match ticket-hygiene.md valid list), suggest based on summary, description, and epic keywords:

| Keywords in summary/description | Suggested component area |
|---------------------------------|--------------------------|
| API, search, query, database, config, presenter | API service |
| adapter, task-config, reconcil | Adapter framework |
| sentinel, watcher | Sentinel service |
| architecture, docs, design, standards | Architecture/docs |
| e2e, test suite, test infrastructure | E2E testing |
| CI, CD, prow, konflux, pipeline, release automation | CI/CD |
| terraform, helm, deployment, infra | Infrastructure |
| claude, plugin, skill | Claude plugins |
| OCI, artifact, chart publishing | OCI distribution |
| broker, pub/sub, rabbitmq, cloudevents | Message broker |

Map the area to the exact component name from ticket-hygiene.md.

## Story Points

Validate against the story point scale defined in ticket-hygiene.md.

- **Missing**: use the `hyperfleet-jira:jira-story-pointer` skill to estimate
- **Too large** (exceeds scale): flag that the ticket MUST be split into smaller stories
- **Not in scale**: suggest the nearest valid value
