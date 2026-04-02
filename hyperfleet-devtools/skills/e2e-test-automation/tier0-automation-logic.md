# Tier0 Test Automation Logic

## Overview

Tier0 tests use **pre-deployed adapters** that are already running in the test environment. These tests assume adapters are available and ready before the test starts.

**Key Principle**: Never deploy or undeploy adapters within Tier0 tests. Adapters are part of the base deployment.

## Characteristics

- **Pre-deployed adapters**: Adapters are deployed BEFORE tests run (in deployment step)
- **Tests assume availability**: Tests assume adapters are already running
- **No adapter lifecycle in test code**: Tests do NOT deploy/undeploy adapters
- **Faster execution**: No adapter deployment overhead
- **Suitable for**: Happy path scenarios, normal workflows, baseline functionality

## What is Tier0?

**Tier0 tests cover critical happy path scenarios that must pass before release.**

| Aspect | Tier0 |
|--------|-------|
| **Priority** | Critical — must pass, blocks release |
| **Test focus** | Critical happy path scenarios, baseline functionality |
| **Adapter lifecycle** | Pre-deployed, shared across tests |
| **Test code** | No adapter deployment/cleanup in test |
| **Examples** | Create cluster and verify it reaches Ready, basic CRUD operations |

**Key Point**: Tier0 = Critical + Happy Path + Pre-deployed adapters

## Adapter Setup Requirements

Before writing Tier0 test automation, verify the required adapters are configured for pre-deployment:

### 1. Adapter Configuration Must Exist

Check that adapter configuration exists in the repository:

```bash
ls testdata/adapter-configs/<adapter-name>/
```

If missing, the adapter cannot be deployed. Ask the test case owner to create it first.

### 2. Add Adapter to Deployment List

Edit `deploy-scripts/.env.example` and add the adapter name to the appropriate list:

**For cluster adapters:**
```bash
CLUSTER_TIER0_ADAPTERS_DEPLOYMENT="adapter1,adapter2,adapter3"
```

**For nodepool adapters:**
```bash
NODEPOOL_TIER0_ADAPTERS_DEPLOYMENT="adapter1,adapter2"
```

### 3. Add Adapter to API Wait List (If Test Waits for Ready)

If your test waits for the resource to reach `Ready=True` condition, you must also add the adapter to the API wait list. This ensures the system waits for this adapter to complete before marking the resource as Ready.

**For cluster adapters:**
```bash
API_ADAPTERS_CLUSTER="adapter1,adapter2,adapter3"
```

**For nodepool adapters:**
```bash
API_ADAPTERS_NODEPOOL="adapter1,adapter2"
```

**Rule**: If adapter is in `CLUSTER_TIER0_ADAPTERS_DEPLOYMENT` AND your test waits for `Ready=True`, then it should also be in `API_ADAPTERS_CLUSTER`. Same for nodepools.

### Example Configuration

```bash
# deploy-scripts/.env.example

# Cluster Tier0 Adapters
CLUSTER_TIER0_ADAPTERS_DEPLOYMENT="cl-maestro,cl-m-ds,cl-quota"
API_ADAPTERS_CLUSTER="cl-maestro,cl-m-ds,cl-quota"

# NodePool Tier0 Adapters
NODEPOOL_TIER0_ADAPTERS_DEPLOYMENT="np-maestro,np-validator"
API_ADAPTERS_NODEPOOL="np-maestro,np-validator"
```

## Test Implementation Pattern

### Test Structure

**No adapter deployment code in BeforeEach or test body.**

```text
Describe("Tier0 Test Suite")
  BeforeEach:
    - (Optional) Create resource if needed by all tests in suite

  It("test description"):
    - Create resource (or use pre-created one)
    - Verify API responses
    - Verify resources via K8s/Maestro
    - Verify conditions

  AfterEach:
    - Cleanup resource
    - (No adapter cleanup - adapters remain deployed)
```

### Preconditions

Before running Tier0 tests, verify:

1. **Adapters are deployed**: Check that required adapters are running in the cluster
2. **Adapters are healthy**: Verify adapter pods are Ready
3. **API is available**: HyperFleet API is reachable
4. **Sentinel is running**: Sentinel is processing events

**Note**: These preconditions are typically verified once at suite setup, not per-test.

### Workflow Steps

Every Tier0 test follows the standard 4-step E2E workflow:

**1. Create Resource**
- Use helper client methods to create resource from payload
- Check error, verify returned ID

**2. Verify via API**
- Get resource statuses via API
- Get resource details via API
- Check conditions (resource-level and adapter-level)
- Verify all required adapters have executed

**3. Verify Resources (if needed)**
- Use K8s helpers, Maestro, or third-party clients to verify actual resources
- Verify resource isolation, metadata, labels, etc.

**4. Cleanup**
- Use helper cleanup methods in AfterEach
- Always check if resources exist before cleanup
- **Do NOT cleanup adapters** - they remain deployed for other tests

### Implementation Mapping Template

When creating the implementation mapping for Tier0 tests, use this template:

```markdown
## Test Case: [Test Title]

### Test Tier: Tier0

### Adapter Requirements
- Required adapters: [adapter1, adapter2, adapter3]
- Already in deployment list: ✅ / ❌
  - CLUSTER_TIER0_ADAPTERS_DEPLOYMENT or NODEPOOL_TIER0_ADAPTERS_DEPLOYMENT
- Waits for Ready: [Yes/No]
  - If Yes, verify in API_ADAPTERS_CLUSTER or API_ADAPTERS_NODEPOOL: ✅ / ❌

### Implementation Plan

**Ginkgo Structure:**
- Suite: `ginkgo.Describe("[Suite: <feature>][<tier>] <Suite Title>")`
- Test: `ginkgo.It("<test description>")`

**Setup (BeforeEach):**
- [Optional: Create resource if needed by all tests]

**Test Steps Mapping:**

| Design Step | Implementation Approach | Helper/Client Method | Gomega Assertion |
|-------------|------------------------|---------------------|------------------|
| Step 1: Submit API request to create resource | Use helper client create method | Create<Resource>FromPayload(ctx, path) | Expect(err).NotTo(HaveOccurred()) |
| Step 2: Verify initial status | Use helper client get method + condition check | Get<Resource>(ctx, id), HasResourceCondition() | Expect(hasCondition).To(BeTrue()) |
| Step 3: Verify adapter execution | Use helper client get statuses + condition check | Get<Resource>Statuses(ctx, id), HasAdapterCondition() | Eventually(...).Should(Succeed()) |
| Step 4: Verify final resource state | Use helper wait for condition | WaitFor<Resource>Condition(ctx, id, type, status, timeout) | Expect(err).NotTo(HaveOccurred()) |

**Teardown (AfterEach):**
- Cleanup resource
- **No adapter cleanup** - adapters remain deployed

**Test Data Required:**
- Payload file: Use existing payload from `testdata/payloads/<resource-type>/` that meets the requirement, or create new if needed (filename doesn't need to follow strict pattern)

**Labels:**
- Priority label: `labels.Tier0`
- Suite label: `[Suite: <resource>][<category>]`
```

## Common Patterns

### Pattern 1: Simple Resource Creation and Verification

**Test Case**: Create resource, verify it reaches Ready state

```text
BeforeEach:
  - (No pre-created resource)

It "should create resource and reach Ready state":
  - Create resource from payload
  - Verify initial status (Ready=False)
  - Wait for Ready=True condition
  - Verify Available=True condition

AfterEach:
  - Cleanup resource
```

### Pattern 2: Adapter Execution Verification

**Test Case**: Verify all required adapters execute successfully

```text
BeforeEach:
  - Create resource (used by all tests in suite)

It "should execute all required adapters":
  - Get resource statuses
  - Verify each required adapter has status
  - Verify Applied=True for each adapter
  - Verify Available=True for each adapter
  - Verify Health=True for each adapter

AfterEach:
  - Cleanup resource
```

### Pattern 3: Resource Isolation Verification

**Test Case**: Verify resource has isolated K8s namespace

```text
BeforeEach:
  - Create resource

It "should create isolated K8s resources":
  - Wait for Ready=True
  - Verify namespace exists with correct labels
  - Verify namespace is Active
  - Verify resources in namespace match expected state

AfterEach:
  - Cleanup resource
```

## Summary

**Tier0 Test Checklist**:
- ✅ Required adapters are in deployment list (`CLUSTER_TIER0_ADAPTERS_DEPLOYMENT` or `NODEPOOL_TIER0_ADAPTERS_DEPLOYMENT`)
- ✅ If test waits for Ready, adapters are in API list (`API_ADAPTERS_CLUSTER` or `API_ADAPTERS_NODEPOOL`)
- ✅ No adapter deployment code in test
- ✅ No adapter cleanup code in AfterEach
- ✅ Standard 4-step workflow: Create → Verify API → Verify Resources → Cleanup
- ✅ Use helper methods for all operations
- ✅ Use `Eventually()` for async operations
- ✅ Verify all required adapters executed successfully
