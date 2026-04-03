---
name: e2e-test-automation
description: |
  TRIGGER: When user asks to "implement", "automate", "generate" a test automation from a test case document.
  WHAT IT DOES: Maps test case steps to the existing HyperFleet E2E internal library architecture (pkg/) to ensure declarative, maintainable code.
argument-hint: <test-case-document-path>
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
| **1** | `exec.Command` (Shell) | ❌ **FORBIDDEN** | **NEVER** use for kubectl or any command with a library equivalent. **ALLOWED** for Helm and adapter deployment scripts. |

---

## 2. Execution Workflow (The "Structural Learning" Protocol)

### Phase 1: Architectural Learning & Folder Usage
1. **Map the Pkg Tree**: Run `ls -R pkg/` to understand the folder structure and domain organization.
2. **Identify Core Models**: Read `pkg/` to understand how resources and states are represented.
3. **Analyze Signature Patterns**: Study how existing wrappers in `pkg/` handle `context`, error management, and resource state.
4. **Learn the Library**: Before automating, `grep -r "func"` in `pkg/` to see the available vocabulary.
   * **If a helper exists**: Use it directly.
   * **If a helper is missing**: **Create a new one** following the exact style, folder usage, and signature patterns of similar functions in `pkg/`.
5. **Identify Adapter Context**: From the test case document and codebase, extract:
   * **Adapter name**: Look for adapter references in test case (e.g., "VMware vSphere", "AWS", "Azure")
   * **Adapter folder**: Search for the adapter in `adapters/` directory (e.g., `adapters/vmware-vsphere/`)
   * **Preparation steps**: Check adapter README or deployment manifests for setup requirements
   * **Test description**: Extract the exact test description that will be used in the `It()` block

### Phase 2: The "Anti-Imperative" Gate
1. **The Verification Gate**: You are **PROHIBITED** from using raw client calls (e.g., `h.MastroClient.Get...` or `h.K8sClient.AppsV1()...`).
2. **Mandatory Abstraction**: You must find or create a helper (e.g., `h.GetMastroResource`, `h.GetDeployment`) that abstracts the low-level client logic, handling context and retries automatically.

### Phase 3: Code Generation & Cleanup
1. **Declarative Implementation**: Write the test using the discovered or replicated library functions.
2. **AfterEach Cleanup**: Always use `AfterEach` blocks with nil checks for reliable teardown.
3. **Logic Fallback**: Follow lifecycle logic based on the test tier:
   * **Tier0** (pre-deployed adapters): [Tier0 automation logic](./tier0-automation-logic.md)
   * **Tier1/Tier2** (hot-plugged adapters): [Tier1/Tier2 automation logic](./tier1-tier2-automation-logic.md)

### Phase 4: Definition of Done (DoD)
- [ ] **Structural Alignment**: Test code uses **zero** `exec.Command` for K8s/Standard tasks and **zero** raw `h.K8sClient`.
- [ ] **Pattern Replication**: Generated code matches the "native" style of the `pkg/` folder usage.
- [ ] **Doc Synchronized**: Metadata updated to `Automation: Automated`.
- [ ] **Traceability**: Final summary identifies which `pkg/` patterns were learned and applied.
- [ ] **Adapter Details**: Real adapter name, actual folder path, and specific preparation steps provided (no placeholders).
- [ ] **Run Instructions**: Actual test description from `It()` block used in ginkgo focus commands (no placeholders).

---

## Summary Template

**IMPORTANT**: Replace ALL placeholders below with actual values discovered during test automation.

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
