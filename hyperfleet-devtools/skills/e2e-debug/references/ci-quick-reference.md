# HyperFleet CI Quick Reference

## Prow Nightly Jobs (main)

| Job | Label Filter | Schedule | Notes |
|-----|-------------|----------|-------|
| `periodic-ci-openshift-hyperfleet-hyperfleet-e2e-main-e2e-tier0-nightly` | `tier0` | Daily | Blocks release |
| `periodic-ci-openshift-hyperfleet-hyperfleet-e2e-main-e2e-tier1-nightly` | `tier1` | Daily | |
| `periodic-ci-openshift-hyperfleet-hyperfleet-e2e-main-e2e-tier2-nightly` | `tier2` | Daily | |

## Release Candidate Jobs

Jobs follow the pattern `periodic-ci-openshift-hyperfleet-hyperfleet-e2e-<branch>-e2e-<tier>-candidate`. Known release branches: `release-0.1`, `release-0.2`, `release-0.3`. Check which branches are active — new release branches may be added.

| Job (release-0.2) | Label Filter |
|-----|-------------|
| `periodic-ci-openshift-hyperfleet-hyperfleet-e2e-release-0.2-e2e-tier0-candidate` | `tier0` |
| `periodic-ci-openshift-hyperfleet-hyperfleet-e2e-release-0.2-e2e-tier1-candidate` | `tier1` |

| Job (release-0.3) | Label Filter |
|-----|-------------|
| `periodic-ci-openshift-hyperfleet-hyperfleet-e2e-release-0.3-e2e-tier0-candidate` | `tier0` |
| `periodic-ci-openshift-hyperfleet-hyperfleet-e2e-release-0.3-e2e-tier1-candidate` | `tier1` |

## GCS Artifact Structure

```text
<job-run-id>/
├── build-log.txt                         # Top-level ci-operator log
├── artifacts/
│   ├── ci-operator.log
│   ├── junit_operator.xml
│   └── <tier>-<variant>/                 # tier0-nightly, tier1-nightly, tier0-candidate, etc.
│       ├── openshift-hyperfleet-e2e-setup/
│       │   ├── build-log.txt             # Setup step log (deploy script output)
│       │   └── artifacts/                # Component logs captured here
│       │       ├── api-hyperfleet-api-*-logs.txt
│       │       ├── api-hyperfleet-api-postgresql-*-logs.txt
│       │       ├── sentinel-clusters-*-logs.txt
│       │       ├── sentinel-nodepools-*-logs.txt
│       │       ├── adapter-clusters-cl-*-logs.txt
│       │       ├── adapter-nodepools-np-*-logs.txt
│       │       └── all-resources.txt     # Full K8s resource dump
│       ├── openshift-hyperfleet-e2e-test/
│       │   ├── build-log.txt             # Test output (Ginkgo results)
│       │   └── artifacts/
│       │       └── junit.xml             # JUnit test report
│       ├── openshift-hyperfleet-e2e-cleanup-cluster-resources/
│       │   └── build-log.txt
│       └── openshift-hyperfleet-e2e-cleanup-cloud-provider/
│           └── build-log.txt
├── build-logs/                           # Image build logs
└── build-resources/                      # Build resource metadata
```

## URL Mapping

- **Prow UI:** `https://prow.ci.openshift.org/view/gs/test-platform-results/logs/<job-name>/<run-id>`
- **GCS web:** `https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/logs/<job-name>/<run-id>/`

## Key Repos

hyperfleet-api, hyperfleet-adapter, hyperfleet-sentinel, hyperfleet-broker, hyperfleet-e2e, hyperfleet-chart

## Environment Details

| Setting | Value |
|---------|-------|
| API base path | `/api/hyperfleet/v1/` (not `/v1/`) |
| API port | 8000 (not 8080) |
| Namespace (local) | `hyperfleet-e2e-$USER` |
| Namespace (CI) | `e2e-<run-id>` (e.g., `e2e-2058843047478693888`) |

## External Resources

- **Slack:** `#hyperfleet-e2e-status`
- **Prow dashboard:** [prow.ci.openshift.org](https://prow.ci.openshift.org/)
- **Prow setup guide:** [add-hyperfleet-e2e-ci-job-in-prow.md](https://github.com/openshift-hyperfleet/architecture/blob/main/hyperfleet/docs/test-release/add-hyperfleet-e2e-ci-job-in-prow.md)

## Manual Rerun

**From CLI (gangway API):**
```bash
curl -v -X POST \
  -H "Authorization: Bearer $(oc whoami -t)" \
  -d '{"job_name": "periodic-ci-openshift-hyperfleet-hyperfleet-e2e-main-e2e-tier0-nightly", "job_execution_type": "1"}' \
  https://gangway-ci.apps.ci.l2s4.p1.openshiftapps.com/v1/executions
```

## Important CI Notes

- Prow uses the **commit status API**, not GitHub Checks. `statusCheckRollup` returns null for Prow jobs.
- Components are **not independently releasable**. All components must be from the same commit window.
