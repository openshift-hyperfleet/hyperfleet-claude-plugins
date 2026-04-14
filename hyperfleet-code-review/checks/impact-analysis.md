# Impact and call chain analysis

This check is **language-agnostic** and runs for every diff regardless of file types.

For each changed struct, config field, function signature, or behavioral change **in the diff**:

- **Trace callers AND callees** of modified functions/types to verify the change is consistent
  in all contexts where it's used
- **Search the codebase** (`Grep`/`Glob`) for consumers that may need updates but weren't
  included in the diff
- **Cross-reference completeness**: if the diff introduces N options/operators/fields/modes,
  verify that ALL N work in ALL contexts (e.g., an operator that works for regular fields may
  fail for JSONB fields; a config that works for clusters may not work for nodepools)
- Use the Agent tool with subagent_type=Explore if the call chain spans more than 3 files

Surface impacted files that are NOT part of the diff as WARN lines in the output, not numbered
findings. Only create numbered findings for files that ARE in the diff.
