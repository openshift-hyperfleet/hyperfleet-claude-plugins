# Tier1/Tier2 Test Automation Logic - Hot-Plugging Adapters

## Overview

Tier1/Tier2 tests require **test-specific adapters** that are NOT part of the base deployment. These tests deploy adapters at test start, run the test, then clean up the adapters.

**Key Principle**: Deploy test-specific adapters → Run test → Undeploy adapters. Never destroy the base deployment environment.

## Characteristics

- **Test-specific adapters**: Adapters deployed ONLY for this test
- **Hot-plugging**: Deploy adapter during test setup, undeploy during teardown
- **Isolated from base deployment**: Base adapters remain untouched
- **Suitable for**: Negative tests, edge cases, failure scenarios, adapter-specific behavior

## Prerequisites

Before writing Tier1/Tier2 test automation:

### 1. Adapter Configuration Must Exist

**CRITICAL**: Test-specific adapter configuration must exist in the repository BEFORE automating the test.

```bash
# Check adapter config exists
ls testdata/adapter-configs/<adapter-name>/
```

**If missing**:
- The adapter cannot be deployed
- Ask the test case owner to create the adapter configuration first
- Do NOT proceed with test automation until config exists

### 2. Adapter Name from Test Case Document

The test case document should specify which adapter to use. Adapter names are NOT hardcoded in the skill.

**Test Case Document Example**:
```markdown
## Test Title: Cluster can reflect adapter failure in top-level status

### Preconditions
- HyperFleet API is running
- Test-specific adapter: `cl-failure-sim` (simulates adapter failure)
- Adapter configuration: `testdata/adapter-configs/cl-failure-sim/`

### Test Steps
...
```

**What to extract**:
- Adapter name: `cl-failure-sim`
- Adapter config path: `testdata/adapter-configs/cl-failure-sim/`

## Test Implementation Pattern

### Test Structure

**Adapters are deployed in BeforeEach and undeployed in AfterEach.**

```text
Describe("Tier1/Tier2 Test Suite")
  BeforeEach:
    - Deploy test-specific adapter(s)
    - Wait for adapter Ready
    - (Optional) Create resource

  It("test description"):
    - Create resource (or use pre-created one)
    - Verify API responses (may include failure scenarios)
    - Verify adapter-specific behavior
    - Verify conditions

  AfterEach:
    - Cleanup resource
    - Undeploy test-specific adapter(s)
    - (Base adapters remain deployed)
```

### Workflow Steps

Every Tier1/Tier2 test follows this workflow:

**1. Deploy Test-Specific Adapter (BeforeEach)**
- Use deployment scripts to deploy adapter
- Wait for adapter pod to be Ready
- Verify adapter is registered with HyperFleet API

**2. Create Resource**
- Use helper client methods to create resource from payload
- Check error, verify returned ID

**3. Verify via API**
- Get resource statuses via API
- Get resource details via API
- Check conditions (resource-level and adapter-level)
- **May verify failure conditions** (Applied=False, Available=False, etc.)

**4. Verify Adapter-Specific Behavior**
- Use K8s helpers, Maestro, or third-party clients
- Verify test-specific adapter behavior (e.g., failure reflection, metadata)

**5. Cleanup (AfterEach)**
- Cleanup resource using helper methods
- **Undeploy test-specific adapter(s)**
- Verify base adapters are untouched

### Implementation Mapping Template

When creating the implementation mapping for Tier1/Tier2 tests, use this template:

```markdown
## Test Case: [Test Title]

### Test Tier: Tier1 / Tier2

### Adapter Requirements
- Test-specific adapter: {adapter-name from test case document}
- Configuration exists: ✅ / ❌
  - Path: testdata/adapter-configs/{adapter-name}/
  - If ❌: Ask test case owner to create configuration first
- Deploy in test: Yes (BeforeEach)
- Cleanup: AfterEach

### Implementation Plan

**Ginkgo Structure:**
- Suite: `ginkgo.Describe("[Suite: <feature>][<category>] <Suite Title>")`
- Test: `ginkgo.It("<test description>")`
- Label: `labels.Tier1` or `labels.Tier2`

**Setup (BeforeEach):**
- Deploy test-specific adapter
- Wait for adapter pod Ready
- [Optional: Create resource if needed by all tests]

**Test Steps Mapping:**

| Design Step | Implementation Approach | Helper/Client Method | Gomega Assertion |
|-------------|------------------------|---------------------|------------------|
| Deploy test-specific adapter | Use deployment script | Bash: deploy-adapter.sh | Expect(err).NotTo(HaveOccurred()) |
| Create resource | Use helper client create method | Create<Resource>FromPayload(ctx, path) | Expect(err).NotTo(HaveOccurred()) |
| Verify adapter failure reflected | Get statuses, check adapter conditions | Get<Resource>Statuses(ctx, id), HasAdapterCondition() | Eventually(...).Should(Succeed()) |
| Verify top-level status reflects failure | Get resource, check resource conditions | Get<Resource>(ctx, id), HasResourceCondition() | Expect(...).To(BeTrue()) |

**Teardown (AfterEach):**
- Cleanup resource: `h.CleanupTest<Resource>(ctx, resourceID)`
- Undeploy test-specific adapter
- Verify base adapters untouched

**Test Data Required:**
- Payload file: Use existing payload from `testdata/payloads/<resource-type>/` that meets the requirement, or create new if needed (filename doesn't need to follow strict pattern)
- Adapter config: `testdata/adapter-configs/{adapter-name}/` (must exist)

**Labels:**
- Priority label: `labels.Tier1` or `labels.Tier2`
- Suite label: `[Suite: <resource>][<category>]`
```

## Common Patterns

### Pattern 1: Adapter Failure Reflection

**Test Case**: Verify resource reflects adapter failure in top-level status

```text
BeforeEach:
  - Deploy failure-simulation adapter
  - Wait for adapter Ready

It "should reflect adapter failure in resource status":
  - Create resource from payload
  - Eventually: verify test adapter status shows failure (Applied=False or Available=False)
  - Verify resource top-level conditions reflect failure (Ready=False, Available=False)
  - Verify failure reason/message propagated

AfterEach:
  - Cleanup resource
  - Undeploy failure-simulation adapter
```

### Pattern 2: Adapter Timeout Handling

**Test Case**: Verify system handles adapter timeout correctly

```text
BeforeEach:
  - Deploy timeout-simulation adapter (configured to timeout)
  - Wait for adapter Ready

It "should handle adapter timeout gracefully":
  - Create resource from payload
  - Eventually: verify test adapter status shows timeout condition
  - Verify resource conditions reflect timeout
  - Verify timeout message includes expected details

AfterEach:
  - Cleanup resource
  - Undeploy timeout-simulation adapter
```

### Pattern 3: Multiple Test-Specific Adapters

**Test Case**: Deploy multiple adapters with different configurations

```text
BeforeEach:
  - Deploy adapter1 (success config)
  - Deploy adapter2 (failure config)
  - Wait for both adapters Ready

It "should handle mixed adapter results":
  - Create resource from payload
  - Eventually: verify adapter1 shows success (Applied=True, Available=True)
  - Eventually: verify adapter2 shows failure (Applied=False)
  - Verify resource aggregates both statuses correctly

AfterEach:
  - Cleanup resource
  - Undeploy adapter1
  - Undeploy adapter2
```

## Implementation Examples

### Example 1: Adapter Failure Test (Tier1)

**Test Case Document**: `test-design/testcases/cluster.md`
**Test Title**: "Cluster can reflect adapter failure in top-level status"
**Test-Specific Adapter**: cl-failure-sim (from test case document)

**Adapter Setup Verification**:
```bash
# Verify adapter config exists
ls testdata/adapter-configs/cl-failure-sim/
# Should contain: deployment.yaml, config.yaml, etc.

```

**Implementation Mapping**:
```markdown
## Test Case: Cluster can reflect adapter failure in top-level status

### Test Tier: Tier1

### Adapter Requirements
- Test-specific adapter: cl-failure-sim (from test case document)
- Configuration exists: ✅ testdata/adapter-configs/cl-failure-sim/
- Deploy in test: Yes (BeforeEach)
- Cleanup: AfterEach

### Test Steps Mapping

| Design Step | Implementation |
|-------------|----------------|
| Deploy failure-simulation adapter | Bash: deploy-adapter.sh cl-failure-sim |
| Create cluster via API | CreateClusterFromPayload() |
| Verify adapter failure status | GetClusterStatuses(), check Applied=False for cl-failure-sim |
| Verify top-level status reflects failure | GetCluster(), check Ready=False, verify failure message |
```

**Generated Code Pattern**:
```text
Describe("[Suite: cluster][failure-handling] Cluster Adapter Failure Handling")
  Label: labels.Tier1

  var testAdapterName string = "cl-failure-sim"  // From test case document

  BeforeEach:
    - h = helper.New()
    - Deploy test-specific adapter:
      err := h.DeployAdapter(ctx, deployOpts)
      Expect(err).NotTo(HaveOccurred())
    - Wait for adapter Ready:
      Bash: kubectl wait --for=condition=Ready pod -l app=cl-failure-sim ...
    - Create cluster:
      cluster, err := h.Client.CreateClusterFromPayload(...)
      clusterID = *cluster.Id

  It("should reflect adapter failure in cluster top-level status"):
    - Eventually: verify cl-failure-sim shows failure status
      statuses, _ := h.Client.GetClusterStatuses(ctx, clusterID)
      Find cl-failure-sim in statuses
      Expect Applied=False or Available=False
    - Verify top-level cluster status:
      cluster, _ := h.Client.GetCluster(ctx, clusterID)
      Expect Ready=False
      Expect failure message contains expected details

  AfterEach:
    - Cleanup cluster: h.CleanupTestCluster(ctx, clusterID)
    - Undeploy test-specific adapter:
      err := h.UninstallAdapter(ctx, releaseName, h.Cfg.Namespace)
      Expect(err).NotTo(HaveOccurred())
```

### Example 2: Adapter Metadata Validation (Tier1)

**Test Case Document**: `test-design/testcases/cluster.md`
**Test Title**: "Cluster adapter status includes complete metadata"
**Test-Specific Adapter**: cl-metadata-test (from test case document)

**Implementation Pattern**:
```text
Describe("[Suite: cluster][metadata] Cluster Adapter Metadata Validation")
  Label: labels.Tier1

  var testAdapterName string = "cl-metadata-test"

  BeforeEach:
    - Deploy cl-metadata-test adapter
    - Create cluster

  It("should include complete metadata in adapter status"):
    - Get cluster statuses
    - Find cl-metadata-test in statuses
    - Verify metadata fields:
      - Reason is non-empty
      - Message is descriptive
      - LastTransitionTime is valid timestamp
      - ObservedGeneration matches expected

  AfterEach:
    - Cleanup cluster
    - Undeploy cl-metadata-test adapter
```

## CRITICAL: Never Destroy Base Deployment

**The Most Important Rule**: Test-specific adapters are used to simulate failures WITHOUT destroying the deployment environment.

### ❌ WRONG Approach

```text
Example: Testing "system handles adapter unavailability"

WRONG implementation:
1. Stop/delete base adapter (e.g., cl-maestro)
2. Create resource
3. Verify system handles missing adapter
4. Restart base adapter

Problem:
- Breaks other tests running in parallel
- May leave environment in broken state
- Affects other resources using the base adapter
```

### ✅ RIGHT Approach

```text
Example: Testing "system handles adapter unavailability"

RIGHT implementation:
1. Deploy test-specific adapter configured to simulate unavailability
   - Adapter name from test case: cl-unavailable-sim
   - Config: testdata/adapter-configs/cl-unavailable-sim/
   - Configured to immediately fail or timeout
2. Create resource
3. Verify system handles test adapter's unavailability
4. Cleanup resource
5. Undeploy test-specific adapter
6. Base adapters remain untouched

Benefits:
- Isolated from other tests
- Environment remains stable
- Test is repeatable
```

**Adapter configurations are created by test case owners**, not by this automation skill.


## Summary

**Tier1/Tier2 Test Checklist**:
- ✅ Adapter name is from test case document (not hardcoded)
- ✅ Adapter config exists in `testdata/adapter-configs/<adapter-name>/`
- ✅ BeforeEach deploys test-specific adapter
- ✅ AfterEach undeploys test-specific adapter
- ✅ Base deployment adapters remain untouched
- ✅ Test verifies adapter-specific behavior (failure, timeout, metadata, etc.)
- ✅ Cleanup is guaranteed in AfterEach blocks
- ✅ Standard workflow: Deploy adapter → Create resource → Verify behavior → Cleanup resource → Undeploy adapter
