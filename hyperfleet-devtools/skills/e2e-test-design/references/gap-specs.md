# Gap Specs for Uncovered ACs

For any AC still at NONE or Partial after coverage verification, generate a gap specification so it can be tracked.

```markdown
### GAP-E2E-001: [AC summary]

- **Title:** E2E: [concise description of missing coverage] (< 100 chars)
- **Type:** Story
- **Priority:** [Major if Tier0 gap, Normal if Tier1, Minor if Tier2]
- **Component:** CICD

### What

Design and implement E2E test case for: [AC description]. Currently has [NONE/Partial] coverage.

### Why

- Acceptance criterion from epic [HYPERFLEET-XXX](https://redhat.atlassian.net/browse/HYPERFLEET-XXX)
- [Reason coverage is missing: out of scope for current design, needs team input, deferred to post-MVP, etc.]

### Acceptance Criteria

- Test case document written following E2E test case template
- Test covers: [specific scenarios]
- [If Partial] Extends existing test: [existing test reference]

### Technical Notes

- Related existing tests: [list closest existing tests for reference]
- Design technique: [recommended technique for this gap]
- Suggested tier: [Tier0/Tier1/Tier2]
```

## Rules

- Only generate gap specs for NONE and Partial ACs — never for Full
- Link back to the source epic in the description
- Include the reason from the coverage verification table
- Priority maps from tier: Tier0 gap -> Major, Tier1 -> Normal, Tier2 -> Minor
