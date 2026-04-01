# Configuration Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via the `hyperfleet-architecture` skill). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

Determine the component type to apply the correct checks:

```bash
# API indicators
ls pkg/api/ 2>/dev/null && echo "IS_API"

# Sentinel indicators
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"

# Adapter indicators
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"

# Tooling indicators
basename $(pwd) | grep -qi "tool\|cli\|util" && echo "IS_TOOLING"
```

### Step 3: Find Configuration Code

Search for configuration-related files and patterns:

```bash
# Config files
ls configs/ config/ 2>/dev/null
ls configs/config.yaml config/config.yaml 2>/dev/null

# Config documentation
ls docs/config.md 2>/dev/null

# Viper/cobra usage
grep -rl "viper\.\|cobra\.\|pflag\." --include="*.go" 2>/dev/null

# Environment variable prefix
grep -rn "HYPERFLEET_" --include="*.go" 2>/dev/null | head -20

# Config file loading
grep -rn "SetConfigFile\|ReadInConfig\|--config\|configFile" --include="*.go" 2>/dev/null | head -10

# Config validation
grep -rn "validate\|Validate\|validator" --include="*.go" 2>/dev/null | head -10

# Config display at boot
grep -rn "config.*log\|log.*config\|/config" --include="*.go" 2>/dev/null | head -10

# Flag definitions
grep -rn "StringVar\|IntVar\|BoolVar\|Flags()" --include="*.go" 2>/dev/null | head -20
```

### Step 4: Checks

For each check, verify the code against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Configuration Sources and Precedence

**What to verify:** The application supports all data sources (flags, environment variables, config files, defaults) with the precedence order defined in the standard (flags > env vars > config file > defaults).
**How to find:** Review viper/cobra setup code from Step 3.

#### Check 2: Environment Variable Convention

**What to verify:** All environment variables use `HYPERFLEET_` prefix and `UPPER_SNAKE_CASE` as required by the standard. Check for env vars that don't follow the convention.
**How to find:** `grep -rn "os.Getenv\|Setenv\|BindEnv\|AutomaticEnv\|SetEnvPrefix" --include="*.go" 2>/dev/null`

#### Check 3: Command-Line Flag Convention

**What to verify:** Flags use lowercase kebab-case and follow the standard's naming hierarchy (e.g., `--server-port`, `--db-host`).
**How to find:** Review flag definitions from Step 3.

#### Check 4: Config File Path Resolution

**What to verify:** Config file location follows the standard: `--config` flag, then `HYPERFLEET_CONFIG` env var, then default paths (`/etc/hyperfleet/config.yaml` for production, `./configs/config.yaml` for development).
**How to find:** Review config file loading code from Step 3.

#### Check 5: Property Naming in Files

**What to verify:** Config properties in YAML files use `snake_case` as required by the standard. **Exception:** Helm values files (`values.yaml`) follow the Helm convention of `camelCase`.
**How to find:** `cat configs/config.yaml config/config.yaml 2>/dev/null | head -30`

#### Check 6: Configuration Validation

**What to verify:** Configuration is validated at startup with proper error handling: full field path, validation rule, actual value, and helpful hints as specified in the standard. Invalid config must exit with code 1.
**How to find:** Review validation code from Step 3.

#### Check 7: Unknown Field Handling

**What to verify:** Unknown/unexpected fields in config files trigger errors (e.g., using `viper.UnmarshalExact()` or equivalent) as required by the standard.
**How to find:** `grep -rn "UnmarshalExact\|DecoderConfig\|ErrorUnused\|DisallowUnknownFields" --include="*.go" 2>/dev/null`

#### Check 8: Configuration Documentation

**What to verify:** A `docs/config.md` exists documenting all configuration options, their data sources, defaults, and any exceptions as required by the standard.
**How to find:** `ls docs/config.md 2>/dev/null`

#### Check 9: Configuration Display

**What to verify:** Merged configuration is displayed at boot time or exposed via a query method (e.g., `/config` endpoint). Sensitive values must be redacted as `**REDACTED**`.
**How to find:** Review config display code from Step 3.

#### Check 10: No Runtime Reloading

**What to verify:** The application does not implement runtime configuration reloading, following the standard's restart-based approach.
**How to find:** `grep -rn "WatchConfig\|OnConfigChange\|fsnotify\|reload.*config" --include="*.go" 2>/dev/null`

## Output Format

```markdown
# Configuration Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter / Tooling]
**Files Reviewed:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Config Sources & Precedence | PASS/PARTIAL/FAIL | 0/N |
| Environment Variable Convention | PASS/PARTIAL/FAIL | 0/N |
| Command-Line Flag Convention | PASS/PARTIAL/FAIL | 0/N |
| Config File Path Resolution | PASS/PARTIAL/FAIL | 0/N |
| Property Naming | PASS/PARTIAL/FAIL | 0/N |
| Configuration Validation | PASS/PARTIAL/FAIL | 0/N |
| Unknown Field Handling | PASS/PARTIAL/FAIL | 0/N |
| Configuration Documentation | PASS/FAIL | 0/N |
| Configuration Display | PASS/PARTIAL/FAIL | 0/N |
| No Runtime Reloading | PASS/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-CFG-001: [Brief description]
- **File:** `path/to/file.go:42`
- **Found:** [what exists in the code]
- **Expected:** [what the standard requires]
- **Severity:** Critical/Major/Minor
- **Suggestion:** [specific remediation]

---

## Recommendations

**Critical (fix before merge):**
1. [Issue with file reference]

**Major (should fix soon):**
1. [Issue with file reference]

**Minor (nice to have):**
1. [Issue with file reference]
```

## Error Handling

- If the repo has no Go code: report "No Go code found -- configuration review not applicable"
- If no configuration code is found: report "No configuration patterns found in this repository"
- If the orchestrator did not supply the configuration standard content: report that the standard content is missing and skip the configuration audit
