# Finding categories (ordered by priority)

Assign one of these categories to each finding. When deduplicating findings from multiple
sources, use the highest-priority category.

1. **Bug** — Bugs and logic issues
2. **Security** — Security issues
3. **Architecture** — Inconsistencies with HyperFleet architecture docs
4. **JIRA** — Does not meet JIRA ticket requirements (review-pr only)
5. **Standards** — Deviations from HyperFleet coding standards
6. **Inconsistency** — Internal inconsistencies and contradictions
7. **Deprecated** — Outdated or deprecated versions
8. **Pattern** — Project patterns not followed
9. **Improvement** — Clarity and maintainability improvements

## Default severity by category

**Blocking** (must fix):

| Category | Override to nit when |
|----------|---------------------|
| Bug | cosmetic or edge-case with no user impact |
| Security | theoretical/defense-in-depth only |

**nit** (non-blocking suggestion):

| Category | Override to Blocking when |
|----------|--------------------------|
| Pattern | ignoring it causes bugs or breaks tooling |
| Improvement | readability is so poor it hides a real bug |

Only categories with deterministic rules are listed. Categories like Architecture, JIRA,
Standards, Inconsistency, and Deprecated depend on context an agent cannot reliably assess
(e.g., whether a JIRA criterion is a hard requirement or a nice-to-have, whether a standard
is mandatory or recommended). For these, the agent assigns severity based on the specific
finding. Rules will be added here as patterns emerge from real review output.
