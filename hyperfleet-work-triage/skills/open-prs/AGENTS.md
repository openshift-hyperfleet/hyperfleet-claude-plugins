# /open-prs skill

## Testing

After modifying any file in `scripts/`, run the test suite:

```bash
bash scripts/tests/run-tests.sh
```

All tests must pass before opening a PR. The tests validate:
- Deterministic scoring (`score.jq`): factor scores, overrides, tier assignment, sorting
- Output formatting (`format-output.jq`): Slack and compact modes, emoji correctness, tier visibility
- Edge cases: zero PRs, JIRA unavailable, draft/CI-failing/waiting-on-author overrides

## Architecture

~80% of the skill logic is in deterministic shell/jq scripts. The LLM only handles Factor 4 (diff classification) and Factor 2 refinement (informal blocking signals from JIRA comments).

| Script | What it does |
|--------|-------------|
| `scripts/collect-data.sh` | Parallel data fetching from GitHub + JIRA |
| `scripts/score.jq` | 8-factor scoring, overrides, tier assignment, sorting |
| `scripts/format-output.jq` | Output formatting for compact and Slack modes |

## Key files

- `SKILL.md` — orchestration instructions for the LLM
- `prioritization-algorithm.md` — scoring rubrics (source of truth for `score.jq`)
- `output-format.md` — output templates (source of truth for `format-output.jq`)
