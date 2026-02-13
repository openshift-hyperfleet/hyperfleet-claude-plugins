---
name: Architecture Impact
description: Analyzes code changes in HyperFleet component repositories (API, Sentinel, Adapter, Broker) to determine if architecture documentation needs updates using intelligent keyword extraction and content search. Activates when users ask "analyze architecture impact", "check if docs need update", or use /architecture-impact.
---

# Architecture Impact Analyzer

This skill analyzes code changes in HyperFleet component repositories and determines whether architecture documentation in the `openshift-hyperfleet/architecture` repository needs to be updated.

## When to Use This Skill

This skill activates automatically when users:
- Ask "analyze architecture impact"
- Ask "check if docs need update"
- Ask "should I update architecture docs?"
- Request analysis of documentation impact from code changes
- Want to know if their PR requires architecture documentation updates

## Prerequisites

**Zero setup required!**

This skill automatically manages the architecture repository:
- First run: Automatically clones architecture repository to cache
- Subsequent runs: Automatically updates architecture repository (git pull)

The architecture repository is cached at:
```
~/.claude/plugins/cache/hyperfleet-devtools/architecture/
```

## Features

**Supported Components:**
- ✅ hyperfleet-api (API Service component)
- ✅ hyperfleet-sentinel (Sentinel polling service)
- ✅ hyperfleet-adapter (Adapter event handler framework)
- ✅ hyperfleet-broker (Broker messaging library)

**Analysis Scope:**
- ✅ Uncommitted changes (default)
- ✅ Git commit range (e.g., `main..HEAD`)
- ✅ Last N commits (e.g., last 5)

**Analysis Method:**
- **Intelligent Keyword Extraction**: LLM analyzes code changes to extract meaningful search terms
- **Content-Based Search**: grep searches actual document content for extracted keywords
- **Validation**: LLM reads candidate documents to confirm they need updating
- **Adaptive Optimization**: Automatically refines keywords if results are too broad or narrow

**Parameters:**
- `--range <git-range>`: Analyze commits in a git range (e.g., `--range main..HEAD`)
- `--last <n>`: Analyze last N commits (e.g., `--last 5`)

## Execution Workflow

### Phase 1: Environment Validation

Verify the execution environment and prerequisites:

1. **Detect Current Repository and Component Type**
   ```bash
   # Get repository name from git remote and extract component name
   REPO_URL=$(git remote get-url origin)
   COMPONENT=$(echo "$REPO_URL" | grep -oE "hyperfleet-(api|sentinel|adapter|broker)")

   # Set component type based on detected component
   case $COMPONENT in
     hyperfleet-api)      COMPONENT_TYPE="API Service" ;;
     hyperfleet-sentinel) COMPONENT_TYPE="Sentinel" ;;
     hyperfleet-adapter)  COMPONENT_TYPE="Adapter" ;;
     hyperfleet-broker)   COMPONENT_TYPE="Broker" ;;
   esac
   ```

   **Requirements:**
   - Must be in a HyperFleet component repository (api, sentinel, adapter, or broker)
   - If not in a supported repository, show error:
     ```
     ❌ Error: Component not supported

     Current repository: {detected_repo}

     This skill supports the following HyperFleet components:
     - hyperfleet-api (API Service)
     - hyperfleet-sentinel (Sentinel)
     - hyperfleet-adapter (Adapter)
     - hyperfleet-broker (Broker)

     Navigate to a supported repository and try again.
     ```

2. **Parse Parameters and Determine Analysis Scope**
   ```bash
   # Parse optional parameters
   RANGE=""
   LAST=""

   # Check for --range parameter
   if [[ "$@" =~ --range[[:space:]]+([^[:space:]]+) ]]; then
     RANGE="${BASH_REMATCH[1]}"
     SCOPE="range:$RANGE"
   fi

   # Check for --last parameter
   if [[ "$@" =~ --last[[:space:]]+([0-9]+) ]]; then
     LAST="${BASH_REMATCH[1]}"
     SCOPE="last:$LAST"
   fi

   # Default: uncommitted changes
   if [ -z "$SCOPE" ]; then
     SCOPE="uncommitted"
   fi
   ```

3. **Verify Git Status**
   ```bash
   # Check if we're in a git repository
   git rev-parse --git-dir

   # Check if there are changes based on scope
   if [ "$SCOPE" == "uncommitted" ]; then
     git status --porcelain
     # If no changes, show friendly message
   elif [[ "$SCOPE" =~ ^range: ]]; then
     # Validate git range
     git rev-parse "$RANGE" 2>/dev/null || {
       echo "❌ Error: Invalid git range: $RANGE"
       exit 1
     }
   elif [[ "$SCOPE" =~ ^last: ]]; then
     # Validate we have enough commits
     COMMIT_COUNT=$(git rev-list --count HEAD)
     if [ "$COMMIT_COUNT" -lt "$LAST" ]; then
       echo "⚠️  Warning: Only $COMMIT_COUNT commits available, requested last $LAST"
     fi
   fi
   ```

   **Requirements:**
   - Must be in a valid git repository
   - For uncommitted analysis: must have changes (modified, added, or deleted files)
   - For range analysis: git range must be valid
   - If no changes (uncommitted mode), show friendly message:
     ```
     ℹ️  No code changes detected

     There are no uncommitted changes to analyze.

     Options:
     - Make code changes and run this skill again
     - Use --range to analyze a commit range (e.g., --range main..HEAD)
     - Use --last to analyze recent commits (e.g., --last 5)
     ```

4. **Ensure Architecture Repository Exists**

   Use the ensure_arch_repo.sh script to clone/update the architecture repository:

   ```bash
   ARCH_REPO=$(bash {skill_base_directory}/ensure_arch_repo.sh)

   if [ $? -ne 0 ] || [ -z "$ARCH_REPO" ]; then
     echo "❌ Error: Failed to ensure architecture repository"
     exit 1
   fi

   echo "✅ Architecture repository ready: $ARCH_REPO"
   ```

   **What this does:**
   - Checks if cached architecture repository exists at `~/.claude/plugins/cache/hyperfleet-devtools/architecture/`
   - If not exists: clones from GitHub
   - If exists: updates with `git pull origin main`
   - Returns the architecture repository path

### Phase 2: Launch Analysis Agent

Once environment validation passes, launch the specialized architecture-impact-analyzer agent:

```
Use Task tool with:
- subagent_type: "hyperfleet-devtools:architecture-impact-analyzer:architecture-impact-analyzer"
- description: "Analyze architecture impact"
- prompt: "Analyze code changes in {repo_name} and determine architecture documentation impact.

          Repository: {repo_name}
          Component Type: {component_type}
          Analysis Scope: {scope}
          Git Range: {range} (if applicable)
          Last N Commits: {last} (if applicable)

          Please provide a detailed impact analysis report."
```

**Context Passed to Agent:**
- Repository name (e.g., "hyperfleet-api", "hyperfleet-sentinel", "hyperfleet-adapter", "hyperfleet-broker")
- Component type (e.g., "API Service", "Sentinel", "Adapter", "Broker")
- Analysis scope (e.g., "uncommitted", "range:main..HEAD", "last:5")

**Expected Agent Output:**
The agent will return a structured markdown report containing:
- Summary (impact level, docs affected)
- Changed files and their impact
- Documentation update recommendations
- Next steps

### Phase 3: Present Results

Format and display the agent's analysis report to the user:

1. **Display Report**
   - Show the complete report to the user
   - Highlight key findings:
     - Impact level (HIGH/MEDIUM/LOW)
     - Number of documents requiring updates
     - Priority of updates (MUST/SHOULD/COULD/WON'T)

2. **Provide Next Steps**
   - If documentation updates are needed:
     ```
     📋 Next Steps:

     1. Review the documentation update recommendations above
     2. Update the identified sections in the architecture repository
     3. Submit a PR to openshift-hyperfleet/architecture
     4. Link the architecture PR to your code PR

     Tip: You can use the hyperfleet-jira:jira-ticket-creator skill to create
     tracking tickets for documentation updates.
     ```

   - If no updates needed:
     ```
     ✅ No architecture documentation updates required

     Your changes don't impact existing architecture documentation.
     You can proceed with your PR.
     ```

## Error Handling

### Error: Not in HyperFleet Repository

```
❌ Error: Not a HyperFleet repository

Current directory: {cwd}
Detected repository: {repo_name}

This skill only works in HyperFleet component repositories.

Supported repositories:
- hyperfleet-api (API Service)
- hyperfleet-sentinel (Sentinel)
- hyperfleet-adapter (Adapter)
- hyperfleet-broker (Broker)

Navigate to a HyperFleet repository and try again.
```

### Error: Unsupported Component

```
❌ Error: Component not supported

Current repository: {repo_name}

This skill supports the following HyperFleet components:
- hyperfleet-api (API Service)
- hyperfleet-sentinel (Sentinel)
- hyperfleet-adapter (Adapter)
- hyperfleet-broker (Broker)

Please navigate to a supported HyperFleet repository and try again.
```

### Error: No Changes Detected

```
ℹ️  No changes to analyze

There are no uncommitted changes in the repository.

To use this skill:
1. Make code changes to your repository
2. Run this skill again before committing

Or use alternative analysis modes:
- --range main..HEAD : Analyze commits in a branch
- --last 5 : Analyze last 5 commits

Examples:
  analyze impact --range main..HEAD
  analyze impact --last 5
```

### Error: Invalid Git Range

```
❌ Error: Invalid git range

Range specified: {range}

The git range is not valid. Please check:
- Both refs exist (e.g., main, HEAD, branch names, commit hashes)
- The range syntax is correct (e.g., main..HEAD, abc123..def456)

Examples of valid ranges:
  --range main..HEAD
  --range feature-branch..HEAD
  --range abc1234..def5678
```

### Error: Architecture Repository Failed

```
❌ Error: Failed to setup architecture repository

The architecture repository could not be cloned or updated.

Possible causes:
- Network connectivity issues
- GitHub authentication required
- Disk space issues

Please check your network connection and try again.
```

### Error: Agent Execution Failed

```
❌ Error: Analysis agent failed

The architecture-impact-analyzer agent encountered an error:
{error_message}

Please try again or contact the HyperFleet DevTools team if the issue persists.

Debug information:
- Repository: {repo_name}
- Component: {component_type}
- Analysis scope: {scope}
```

## Tips for Users

**Before submitting a PR:**
1. Run this skill to check documentation impact
2. Address any HIGH priority documentation updates
3. Create JIRA tickets for MEDIUM/LOW priority updates if needed
4. Link documentation PRs to your code PR

**For best results:**
- Run analysis when your changes are complete but not yet committed
- Review the full report, not just the summary
- Prioritize HIGH impact documentation updates

**Integration with other skills:**
- Use `hyperfleet-jira:jira-ticket-creator` to create tracking tickets for doc updates
- Use `hyperfleet-architecture` to understand existing documentation structure
