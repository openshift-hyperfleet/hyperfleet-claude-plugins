---
name: e2e-test-automation
description: |
  TRIGGER: When user asks to "implement", "automate", "generate", "update" test automation from a test case document or existing test code.
  WHAT IT DOES: Creates new or updates existing test automation by mapping test case steps to the HyperFleet E2E internal library architecture (pkg/) to ensure declarative, maintainable code.
argument-hint: <test-case-document-path-or-test-file-path>
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# HyperFleet E2E Test Automation

**Role**: Expert Quality Engineer.
**Strict Mandate**: **Library Abstraction over Shell/API.** You are strictly prohibited from using `exec.Command` or raw `h.K8sClient` for any task where a helper can be discovered or modeled after existing `pkg/` patterns.

---

## 1. The Compatibility Ladder (Non-Negotiable)
You must always move "Up" this ladder. Any move "Down" is an architectural failure.

| Level | Implementation Type | Status | Required Action |
| :--- | :--- | :--- | :--- |
| **3** | `h.HelperFunction()` | ✅ **GOAL** | Use/Create high-level wrappers for ALL actions. |
| **2** | `h.K8sClient` (API) | ❌ **FORBIDDEN** | Never use for standard CRUD/Scale operations. |
| **1** | `exec.Command` (Shell) | ❌ **FORBIDDEN** | **NEVER** use in test code for kubectl or any command with a library equivalent. Helm operations in test code must use helpers (e.g., `h.DeployAdapter`, `h.UninstallAdapter`). **ALLOWED** only in helper implementations for Helm commands. |

---

## 2. Execution Workflow (The "Structural Learning" Protocol)

### Phase 0: Scenario Detection
1. **Extract Test Metadata**: From the test case document, identify:
   * **Test title/description**: The exact description that will be used in the `It()` block
   * **Resource type**: What K8s/HyperFleet resource is being tested (e.g., Deployment, ManagedCluster)
2. **Search for Existing Test Code**:
   * Search in `e2e/` directory for test files containing the test title/description
   * Use `grep -r "It(\"<test-description>\"" e2e/` or similar patterns
3. **Determine Scenario**:
   * **Scenario 1 (New)**: No existing test code found → Proceed with full automation workflow
   * **Scenario 2 (Update)**: Existing test code found → Analyze for:
     - **Logic changes**: Test steps in document differ from code implementation
     - **Implementation quality**: Code uses anti-patterns (raw clients, `exec.Command`, missing helpers)
   * **The Rule**: Update the code if **Logic changed** OR **Implementation Quality** can be improved (Modernization)

### Phase 1: Architectural Learning & Folder Usage
1. **Map the Pkg Tree**: Use `Glob` with pattern `pkg/**/*.go` to explore the folder structure and domain organization.
2. **Identify Core Models**: Use `Read` on key files in `pkg/` to understand how resources and states are represented.
3. **Analyze Signature Patterns**: Study how existing wrappers in `pkg/` handle `context`, error management, and resource state.
4. **Learn the Library**: Before automating, discover available helpers using:
   * `Grep` for pattern `^func ` in `pkg/` — find all function definitions
   * `Grep` for pattern `func \(h \*Helper\)` in `pkg/` — find helper methods specifically
   * **If a helper exists**: Use it directly.
   * **If a helper is missing**: **Create a new one** following the exact style, folder usage, and signature patterns of similar functions in `pkg/`.
5. **Identify Adapter Context**: From the test case document and codebase, extract:
   * **Adapter name**: Look for adapter references in test case (e.g., "VMware vSphere", "AWS", "Azure")
   * **Adapter folder**: Use `Glob` with pattern `adapters/*/` or search for specific adapter (e.g., `adapters/vmware-vsphere/`)
   * **Preparation steps**: Use `Read` on adapter README or deployment manifests for setup requirements
   * **Test description**: Extract the exact test description that will be used in the `It()` block

### Phase 2: The "Anti-Imperative" Gate
1. **The Verification Gate**: You are **PROHIBITED** from using raw client calls (e.g., `h.MaestroClient.Get...` or `h.K8sClient.AppsV1()...`).
2. **Mandatory Abstraction**: You must find or create a helper (e.g., `h.GetMaestroResource`, `h.GetDeployment`) that abstracts the low-level client logic, handling context and retries automatically.

### Phase 3: Code Implementation

**For Scenario 1 (New Test Automation)**:
1. **Declarative Implementation**: Write the test using the discovered or replicated library functions.
2. **AfterEach Cleanup**: Always use `AfterEach` blocks with nil checks for reliable teardown.
3. **Logic Fallback**: Follow lifecycle logic based on the test tier:
   * **Tier0** (pre-deployed adapters): [Tier0 automation logic](./tier0-automation-logic.md)
   * **Tier1/Tier2** (hot-plugged adapters): [Tier1/Tier2 automation logic](./tier1-tier2-automation-logic.md)

**For Scenario 2 (Update Existing Test Automation)**:
1. **Read Existing Test Code**: Understand current implementation and test structure.
2. **Identify Issues**:
   * Anti-patterns: `exec.Command` usage, raw `h.K8sClient` or `h.MaestroClient` calls
   * Logic gaps: Missing steps from test case document
   * Missing cleanup: No `AfterEach` or incomplete teardown
3. **Refactor with Helpers**:
   * Replace `exec.Command` with library equivalents (EXCEPT for Helm/adapter deployment scripts)
   * Replace raw client calls with `pkg/` helpers
   * Add missing test steps from document
   * Ensure proper cleanup in `AfterEach`
4. **Preserve Test Behavior**: Ensure refactored test validates the same conditions as original

### Phase 4: Definition of Done (DoD)

**For Both Scenarios**:
- [ ] **Structural Alignment**: Test code uses **zero** `exec.Command` for K8s/Standard tasks and **zero** raw `h.K8sClient`.
- [ ] **Pattern Replication**: Generated/refactored code matches the "native" style of the `pkg/` folder usage.
- [ ] **Traceability**: Final summary identifies which `pkg/` patterns were learned and applied.
- [ ] **Adapter Details**: Real adapter name, actual folder path, and specific preparation steps provided (no placeholders).
- [ ] **Run Instructions**: Actual test description from `It()` block used in ginkgo focus commands (no placeholders).

**Additional for Scenario 1 (New)**:
- [ ] **Doc Synchronized**: Metadata updated to `Automation: Automated`.

**Additional for Scenario 2 (Update)**:
- [ ] **Test Behavior Preserved**: Refactored test validates the same conditions as original.
- [ ] **Improvement Summary**: Document what anti-patterns were removed and what helpers were introduced.

---

## Summary Template

**IMPORTANT**: Replace ALL placeholders below with actual values discovered during test automation.

### For Scenario 1 (New Test Automation)

```text
✅ Test Code: e2e/<resource>/<file>.go
✅ Patterns Learned/Replicated: [Describe the pkg/ folder usage or wrappers applied]
✅ Test Case Document Updated:
   - File: test-design/testcases/<name>.md
   - Automation: Automated ✓

📦 Adapter Information:
   - Name: [actual adapter name from test case]
   - Folder: [actual adapter folder path, e.g., adapters/vmware-vsphere/]
   - Preparation: [specific steps to prepare this adapter, or "Ensure adapter is deployed in test environment"]

🚀 Run Test Locally:
   After preparing HyperFleet environment:
   
   # Navigate to test directory
   cd e2e/[actual-resource-folder]/
   
   # Run the specific test
   ginkgo -v -focus="[actual test description from It() block]" .
   
   # Or run with go test
   go test -v -ginkgo.focus="[actual test description from It() block]" .
```

### For Scenario 2 (Update Existing Test Automation)

```text
✅ Test Code Updated: e2e/<resource>/<file>.go
✅ Improvements Made:
   - Removed: [list anti-patterns removed, e.g., "3 exec.Command calls", "2 raw h.K8sClient calls"]
   - Added: [list helpers introduced, e.g., "h.GetDeployment", "h.WaitForManagedClusterReady"]
   - Logic: [describe any logic updates from test case document]
✅ Patterns Applied: [Describe the pkg/ folder usage or wrappers applied]
✅ Test Behavior: [confirm original test behavior is preserved]

📦 Adapter Information:
   - Name: [actual adapter name from test case]
   - Folder: [actual adapter folder path, e.g., adapters/vmware-vsphere/]
   - Preparation: [specific steps to prepare this adapter, or "Ensure adapter is deployed in test environment"]

🚀 Run Test Locally:
   After preparing HyperFleet environment:
   
   # Navigate to test directory
   cd e2e/[actual-resource-folder]/
   
   # Run the specific test
   ginkgo -v -focus="[actual test description from It() block]" .
   
   # Or run with go test
   go test -v -ginkgo.focus="[actual test description from It() block]" .
```
