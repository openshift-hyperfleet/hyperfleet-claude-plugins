# JIRA Description Formatting Reference

The `jira-cli` accepts **Markdown** (GitHub-flavored and Jira-flavored) and automatically converts it to ADF (Atlassian Document Format) for JIRA Cloud. Use standard Markdown for descriptions — headers, bullets, bold, inline code, fenced code blocks, and curly braces all render correctly.

## Markdown Example

```markdown
### What

Description paragraph.

### Why

- Reason 1
- Reason 2

### Acceptance Criteria

- `component` created/implemented
- Feature X works correctly:
  - Detail 1
  - Detail 2
- Tests achieve >80% coverage

**Bold text** and `inline code` work as expected.
```

## Code Blocks

Fenced code blocks (triple backticks) work correctly when created via CLI — the `jira-cli` converts them to ADF code block nodes.

## API Endpoints in Descriptions

```text
**POST** /api/v1/clusters/:id              (bold method, colon notation)
**GET** /api/v1/clusters/{id}              (curly braces work too)
```

## Custom Fields

Use field aliases, NOT raw field IDs:

```bash
--custom story-points=3                                    # Correct
--custom activity-type="Quality / Stability / Reliability" # Correct
--custom customfield_10028=3                               # Wrong (silently ignored)
--custom customfield_10464="..."                           # Wrong (silently ignored)
```
