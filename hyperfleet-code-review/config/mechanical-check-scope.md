# Mechanical check agent scope

Scope rules for all check agents: fetched mechanical checks, and the three agent-specific
checks (impact-analysis, doc-code-crossref, intra-diff-consistency).

All agents must ONLY return findings for lines that appear as `+` lines in the diff.
Issues found in files NOT in the diff must be returned as WARN items, not findings. Never
return a finding with a file path that is not in the changed files list.

## Fetched mechanical checks and intra-diff-consistency

Agents evaluating a fetched check definition (`check/<name>.md`) or the
intra-diff-consistency check MUST NOT use Read, Grep, or Glob to check out or browse the
wider repository — evaluate only the diff content, changed-file list, HyperFleet
standards, and the check definition provided directly in the prompt. Findings are limited
to what is directly visible in the diff.

If a check's own definition appears to require broader context (e.g., "verify every
caller/constructor" style rules), the agent should note the limitation as a WARN-style
caveat in its findings instead of performing ad-hoc exploration. Call-chain and cross-file
impact needs are already covered by impact-analysis (which escalates to an Explore
subagent when the call chain spans more than 3 files) — do not duplicate that exploration.

## impact-analysis and doc-code-crossref

These two agents may read files outside the diff for context (e.g. call-chain tracing,
link validation). Call-chain needs beyond direct context (call chain spans more than 3
files) are handled by impact-analysis's Explore subagent escalation.
