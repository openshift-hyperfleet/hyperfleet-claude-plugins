# Configuration Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via `gh api`). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

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
grep -rl "viper\.\|cobra\.\|pflag\." --include="*.go" . 2>/dev/null

# Environment variable prefix — search for the prefix defined in the standard
grep -rn "os.Getenv\|Setenv\|BindEnv\|AutomaticEnv\|SetEnvPrefix" --include="*.go" . 2>/dev/null | head -20

# Config file loading
grep -rn "SetConfigFile\|ReadInConfig\|--config\|configFile" --include="*.go" . 2>/dev/null | head -10

# Config validation
grep -rn "validate\|Validate\|validator" --include="*.go" . 2>/dev/null | head -10

# Config display at boot
grep -rn "config.*log\|log.*config\|/config" --include="*.go" . 2>/dev/null | head -10

# Flag definitions
grep -rn "StringVar\|IntVar\|BoolVar\|Flags()" --include="*.go" . 2>/dev/null | head -20
```

### Step 4: Checks

For each check, verify the code against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Configuration Sources and Precedence

**What to verify:** The application supports all data sources defined in the standard with the precedence order specified in the standard.
**How to find:** Review viper/cobra setup code from Step 3.

#### Check 2: Environment Variable Convention

**What to verify:** All environment variables use the prefix and casing convention required by the standard. Check for env vars that don't follow the convention.
**How to find:** `grep -rn "os.Getenv\|Setenv\|BindEnv\|AutomaticEnv\|SetEnvPrefix" --include="*.go" . 2>/dev/null`

#### Check 3: Command-Line Flag Convention

**What to verify:** Flags follow the casing and naming hierarchy defined in the standard.
**How to find:** Review flag definitions from Step 3.

#### Check 4: Config File Path Resolution

**What to verify:** Config file location follows the resolution order and default paths defined in the standard.
**How to find:** Review config file loading code from Step 3.

#### Check 5: Property Naming in Files

**What to verify:** Config properties in files follow the casing convention required by the standard, including any exceptions defined for specific file types.
**How to find:** `cat configs/config.yaml config/config.yaml 2>/dev/null | head -30`

#### Check 6: Configuration Validation

**What to verify:** Configuration is validated at startup with the error handling behavior specified in the standard (validation output format, exit behavior on invalid config).
**How to find:** Review validation code from Step 3.

#### Check 7: Unknown Field Handling

**What to verify:** Unknown/unexpected fields in config files trigger errors (e.g., using `viper.UnmarshalExact()` or equivalent) as required by the standard.
**How to find:** `grep -rn "UnmarshalExact\|DecoderConfig\|ErrorUnused\|DisallowUnknownFields" --include="*.go" . 2>/dev/null`

#### Check 8: Configuration Documentation

**What to verify:** A `docs/config.md` exists documenting all configuration options, their data sources, defaults, and any exceptions as required by the standard.
**How to find:** `ls docs/config.md 2>/dev/null`

#### Check 9: Configuration Display

**What to verify:** Merged configuration is displayed at boot time or exposed via a query method (e.g., `/config` endpoint). Sensitive values must be redacted using the placeholder defined in the standard.
**How to find:** Review config display code from Step 3.

#### Check 10: No Runtime Reloading

**What to verify:** The application does not implement runtime configuration reloading, following the standard's restart-based approach.
**How to find:** `grep -rn "WatchConfig\|OnConfigChange\|fsnotify\|reload.*config" --include="*.go" . 2>/dev/null`

#### Check 11: Config File Format

**What to verify:** Verify that configuration files use the format required by the standard (e.g., YAML). Flag config files in other formats (TOML, JSON, INI) if the standard mandates YAML.
**How to find:** `ls configs/ config/ 2>/dev/null` — check file extensions against the format required by the standard.

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
| Config File Format | PASS/FAIL | 0/N |

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
