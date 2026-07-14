# Standards and mechanical checks fetch

Run both fetch scripts when the `gh` CLI is available and authenticated (see Dynamic
context). Launch them in parallel within a single Bash call:

```bash
std_out="$(mktemp)"; chk_out="$(mktemp)"
trap 'rm -f "$std_out" "$chk_out"' EXIT
bash CLAUDE_SKILL_DIR/../../scripts/fetch-standards.sh > "$std_out" &
bash CLAUDE_SKILL_DIR/../../scripts/fetch-checks.sh > "$chk_out" &
wait
cat "$std_out" "$chk_out"
```

Replace `CLAUDE_SKILL_DIR` with the resolved skill directory path.

## Output format

Both scripts print delimited sections:

| Prefix | Source script | Content |
|--------|--------------|---------|
| `===== <name>.md =====` | fetch-standards.sh | Standards document |
| `===== component/<name>/<file>.md =====` | fetch-standards.sh | Component doc |
| `===== check/<name>.md =====` | fetch-checks.sh | Mechanical check definition |
| `===== FETCH FAILURES =====` | Either | One or more files failed to fetch |

## Error handling

- If script output contains `FETCH FAILURES`, note it in the calling skill's own
  setup/summary output format (see its output-format.md) and continue without the missing
  files.
- If `gh auth status` was "NOT authenticated" (see Dynamic context), include a hint:
  "Run `gh auth login` to enable standards and checks fetching."
- If all checks fail to fetch, the review can still run using only agent-specific checks
  (local files). Note the degraded state in the calling skill's defined setup/summary
  output as above.

## Mechanical checks usage

Fetched check definitions (prefixed `check/`) are the canonical source for mechanical
review agents. Each agent receives its corresponding check definition as part of its
prompt context. Checks are discovered dynamically from the architecture repo.
