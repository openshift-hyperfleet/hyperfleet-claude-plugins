# `/e2e-debug` — Presentation Outline for Google Slides

> Copy each slide section into a Google Slide. Speaker notes are included below each slide.
> Data period: May 12 – June 5, 2026 (90 Prow nightly runs across 3 tiers).

---

## Slide 1: Title

**Debugging E2E Pipeline Failures at Scale**

*Introducing `/e2e-debug` — an AI-powered forensic debugger for HyperFleet CI*

HyperFleet DevTools | June 2026

> **Speaker notes:**
> This presentation covers a recurring pain point for our team — debugging failed E2E pipeline runs — and a new Claude Code skill that automates the investigation. We'll look at real data from our Prow nightlies, walk through how the tool works, and show it diagnosing actual failures that we've already confirmed against fix commits.

---

## Slide 2: The Problem

**Debugging a failed nightly pipeline today**

A developer investigating a failed E2E run currently has to:

1. Find the Prow job URL and navigate to the GCS artifact browser
2. Figure out which step failed (setup? test? cleanup? cascade?)
3. Read through multi-KB log files to find the `[FAILED]` marker
4. Cross-reference against the debugging handbook (500+ lines)
5. Check recent commits across 6+ repos for potential regressions
6. Search JIRA for known bugs or flaky test tickets
7. Distinguish infrastructure issues (etcd, DNS, node capacity) from code bugs
8. Understand accumulated state issues (Maestro DB, orphaned resources) that aren't in any single run's logs

**Typical time to root cause: 30–90 minutes per failure**

> **Speaker notes:**
> This isn't a hypothetical — this is what we actually do every time a nightly fails. The information is spread across GCS artifacts, GitHub, JIRA, the architecture repo, and sometimes the live cluster. Most of the time is spent on context-gathering, not actual diagnosis. And the tribal knowledge required (like "Maestro's labelSelector is silently ignored") means only a few people can debug certain failure classes effectively.

---

## Slide 3: By the Numbers

**E2E Nightly Pipeline Health — Last 30 Runs per Tier**

| Tier | Runs | Pass | Fail | Aborted/Error | Pass Rate |
|------|:----:|:----:|:----:|:-------------:|:---------:|
| **Tier 0** (blocks release) | 30 | 23 | 6 | 1 | **76.7%** |
| **Tier 1** | 30 | 20 | 7 | 3 | **66.7%** |
| **Tier 2** | 30 | 19 | 11 | 0 | **63.3%** |
| **Combined** | **90** | **62** | **24** | **4** | **68.9%** |

*Data period: May 12 – June 5, 2026*

**~1 in 3 nightly runs fails.** That's a debugging investigation triggered almost every day across the three tiers.

> **Speaker notes:**
> These are real numbers pulled from GCS `finished.json` for every run in the last 25 days. Tier 0 is the healthiest because it blocks the release, so failures get fixed fastest. Tier 2 has the worst pass rate at 63% — at one point it had 4 consecutive failures from May 21-25. The key takeaway: someone on the team is debugging a pipeline failure almost every single day.

---

## Slide 4: What Goes Wrong?

**Failure categories from the last 28 failures (real data)**

| Category | Count | % | Example |
|----------|:-----:|:-:|---------|
| **Code regression** (test or component) | 14 | 50% | `broker.type` validation added to adapter chart but e2e test configs not updated (4-day regression, HYPERFLEET-1104) |
| **Accumulated persistent state** | 5 | 18% | 231 stale Maestro ResourceBundles caused pagination to hide test resources (HYPERFLEET-992) |
| **Prow infrastructure** | 5 | 18% | `etcdserver: mvcc: database space exceeded` on shared cluster |
| **Aborted / cancelled** | 4 | 14% | Manual retriggers superseding stuck runs |

> **Speaker notes:**
> Half our failures are legitimate code regressions — a change in one repo breaks e2e tests in another. These are the ones where fast root-cause analysis matters most, because they block the team until someone investigates. The accumulated state category is the most insidious — logs look completely clean, the API returns 200 OK, but the test gets nil results because Maestro's DB has 231 stale entries from prior runs. PR #79 (HYPERFLEET-992) fixed the Maestro case, but it took days to diagnose because nothing in the logs pointed to the real cause. Infrastructure failures are the simplest to handle (just retry), but you still need to know it's infra vs. code before you retry.

---

## Slide 5: The Real Cost

**What a pipeline failure costs today**

| Impact | Detail |
|--------|--------|
| **Time** | 30–90 min per investigation. At ~1 failure/day across tiers, that's **2.5–7.5 hours/week** of engineering time on debugging |
| **Context switching** | The developer who investigates is usually not the one who caused the regression — they must learn the context cold |
| **Tribal knowledge** | Key debugging patterns (Maestro JSONB queries, Sentinel metrics, Helm ownership conflicts) live in people's heads, not in tooling |
| **Delayed fixes** | The broker.type regression took **4 days** to fix. The Maestro pagination issue took even longer. Every day a nightly stays red, release confidence drops |
| **False retries** | Without diagnosis, the default response is "just retrigger it." ~50% of failures are code regressions that will fail again on retry |

> **Speaker notes:**
> The numbers are conservative. 30 minutes is the fast path for someone who knows the system. For a newer team member, it can take hours. And the false retry rate is the silent killer — half the time we retrigger a job that's going to fail the same way because it's a code bug, not an infra blip. That's wasted CI resources and a delayed diagnosis.

---

## Slide 6: The Solution — `/e2e-debug`

**One command. Full root cause analysis.**

```
/e2e-debug https://prow.ci.openshift.org/view/gs/.../tier1-nightly/2058873327929266176
```

**What it does:**
- Fetches and parses GCS build logs and component artifacts
- Matches errors against 30+ documented failure patterns
- Checks recent commits, PRs, and JIRA for related changes
- Inspects live cluster state (Maestro DB, orphaned resources, metrics)
- Cross-validates findings across multiple sources before reporting
- Outputs a structured, confidence-scored diagnosis with recommended action

**Built as a Claude Code skill in the `hyperfleet-devtools` plugin — available to the whole team.**

> **Speaker notes:**
> This is a Claude Code skill, not a standalone script. It runs inside your Claude Code session and uses the tools you already have (gh, jira, kubectl, gcloud). You invoke it with a Prow URL, a job name, or even a JIRA ticket, and it produces a structured root cause analysis. We validated it against 3 real failures and confirmed the diagnosis matched the actual fix commits in every case.

---

## Slide 7: How It Works

**6-step forensic workflow**

```
Step 1: Log Retrieval          Step 2: Pattern Matching       Step 3: Change Verification
 Fetch GCS artifacts             Match against 30+ known        Check recent commits/PRs
 Determine which step failed     failure patterns                in 6+ repos + JIRA
 Resolve component log names     Check debugging handbook        Check prior run history
 Identify cascade vs root        Flag infra vs code              via GCS finished.json
          │                              │                              │
          └──────────────────────────────┴──────────────────────────────┘
                                         │
                                    Step 4: Synthesis
                                     Formulate hypothesis
                                     Preliminary confidence score
                                         │
                                    Step 5: Live Cluster (optional)
                                     Cross-validate via kubectl/gcloud
                                     Maestro DB, metrics, orphaned resources
                                     Confirm or revise hypothesis
                                         │
                                    Step 6: Certification Gate
                                     Contradiction check
                                     Symptom vs cause check
                                     Two-source corroboration
                                         │
                                      Output
                                     Structured report with
                                     confidence score (HIGH/MEDIUM/LOW)
```

> **Speaker notes:**
> The workflow is designed to be forensic, not optimistic. Step 6 is a mandatory certification gate — the skill must answer three meta-questions before emitting a diagnosis: is there any contradicting evidence? Am I confusing a symptom with a cause? Can I back this up from at least two independent sources? If it can't pass the gate, it outputs LOW confidence with an explicit "DIAGNOSIS UNCERTAIN" and tells you what data it needs to continue. No hallucination, no guesswork.

---

## Slide 8: Real Example — The Broker.Type Regression

**Tier 1 nightly, May 25 — Run `2058873327929266176`**

```
CI Failure Analysis for: tier1-nightly / 2058873327929266176
Confidence: HIGH

1. The Failure Point
   Failing Step: openshift-hyperfleet-e2e-test
   Failing Tests: 5 specs — all Maestro transport negative scenarios
   Exact Error: helm upgrade failed: exit status 1
     Error: execution error at (deployment.yaml:94:31):
     broker.type must be set to one of: googlepubsub, rabbitmq

2. Root Cause Analysis
   The adapter Helm chart (PR #160, HYPERFLEET-1104, May 21) changed
   broker type resolution from inference to a hard `required` call.
   E2E test adapter configs were not updated to include broker.type.

3. Supporting Evidence
   Logs: All 5 failures show identical Helm error at line 94:31
   Related Changes: hyperfleet-adapter PR #160 introduced the validation
   Prior Runs: Last 5: FAIL, FAIL, FAIL, FAIL, PASS (regression pattern)

4. Recommended Action
   Add broker.type: googlepubsub to all test adapter values.yaml files
   under testdata/adapter-configs/
```

> **Speaker notes:**
> This is the actual output format. The diagnosis identifies the exact Helm chart line, the PR that caused the regression, and the correct fix — all confirmed against the real fix commit. The confidence is HIGH because the error message is deterministic and corroborated by both the logs and the git history.

---

## Slide 9: Confirmed Against Fix Commits

**3/3 diagnoses matched the actual fix PRs**

| Failure | Skill's Diagnosis | Actual Fix | Match? |
|---------|-------------------|------------|:------:|
| **Tier 0** — May 12-13 | `Available` condition assertion failing — test expectations changed | API PR #127 renamed `Available` → `LastKnownReconciled`. E2E PR #99 updated tests | Yes |
| **Tier 1** — May 25 | Adapter chart requires `broker.type` but test configs don't pass it | Adapter PR #160 introduced validation. E2E PR #107 added broker config to all test values files | Yes |
| **Tier 2** — May 22 | Same `broker.type` missing from `cl-crash` and `cl-stuck` configs | Same E2E PR #107 fixed it — added broker config to all adapter configs including cl-crash and cl-stuck | Yes |

**The skill identified the correct root cause, the correct component, and the correct fix approach in every case.**

> **Speaker notes:**
> We didn't just test on toy examples — we ran the skill's workflow against real Prow failures and then confirmed the diagnosis against the actual fix commits that were already merged. The tier0 failure was a condition rename that broke across repos. The tier1/tier2 failures traced to the same Helm validation regression with a 4-day regression window. In all three cases, the skill's output would have pointed the developer directly to the fix.

---

## Slide 10: What It Needs

**Prerequisites**

| Tool | Required? | What it's used for |
|------|:---------:|-------------------|
| `gh` CLI | Required | Fetch logs from GCS, debugging handbook, architecture docs, recent commits/PRs |
| `jira` CLI | Optional | Search for related bug tickets and known flaky tests |
| `kubectl` | Optional | Live cluster inspection — Maestro DB state, orphaned resources, pod health, metrics |
| `gcloud` | Optional | Cloud resource inspection — Pub/Sub leaks, GKE cluster health |
| `jq` | Optional | Parse JSON responses from Maestro API and cluster status endpoints |

**Graceful degradation:** The skill checks tool availability at load time and skips steps that require unavailable tools. Core diagnosis (Steps 1-4) works with `gh` alone. Steps 5-6 add live cluster validation when kubectl/gcloud are present.

> **Speaker notes:**
> The minimum requirement is just the gh CLI, which everyone on the team already has. JIRA and kubectl/gcloud add more signal but aren't blocking. The dynamic context section at the top of the skill checks for each tool and adapts the workflow accordingly. If you don't have kubectl, you still get log-based diagnosis with the confidence benchmark — you just miss the live cluster corroboration.

---

## Slide 11: Future — Automated Triggering

**From manual invocation to zero-touch debugging**

**Phase 1: GitHub Action on Prow failure notification**
```yaml
# .github/workflows/e2e-debug-on-failure.yml
on:
  repository_dispatch:
    types: [prow-job-failed]

jobs:
  debug:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          prompt: "/e2e-debug ${{ github.event.client_payload.job_url }}"
```
A Prow post-submit webhook notifies GitHub on failure. The action runs `/e2e-debug` and posts the structured analysis as a GitHub Issue comment.

**Phase 2: Slack integration**
Post the diagnosis to `#hyperfleet-e2e-status` automatically. The team wakes up to a root cause analysis, not just a red build notification.

**Phase 3: Auto-triage**
If confidence is HIGH and the failure is infrastructure → auto-retrigger the job. If it's a code regression → auto-create a JIRA bug with the diagnosis attached and tag the component owner.

> **Speaker notes:**
> The end goal is that no one has to manually investigate a nightly failure. Phase 1 is straightforward — a webhook from Prow triggers a GitHub Action that runs the skill. Phase 2 pipes the output to Slack so the team sees the diagnosis in their daily standup channel. Phase 3 is where it gets interesting — if the skill is confident enough, it can take action: retry for infra issues, or create a JIRA bug and assign it for code regressions. We'd start with Phase 1 and iterate based on the accuracy of the automated diagnoses.

---

## Slide 12: Summary & Next Steps

**What we covered:**
- ~31% of our E2E nightlies fail — that's a daily debugging investigation
- Manual debugging takes 30-90 min and depends on tribal knowledge
- `/e2e-debug` automates the full forensic workflow in minutes
- Validated against 3 real failures — 3/3 matched actual fix commits

**Next steps:**
1. Install the skill: `/plugin marketplace update hyperfleet-claude-plugins`
2. Try it on the next failure: `/e2e-debug <prow-url>`
3. Feedback → iterate → Phase 1 automation

**Available now in `hyperfleet-devtools` v0.6.0**

> **Speaker notes:**
> The skill is merged and available today. The next time a nightly fails, try running it before doing the manual investigation and compare. We want feedback on accuracy, missing failure patterns, and any edge cases where the diagnosis is wrong or LOW confidence. That feedback loop is how we get to Phase 1 automation with confidence.
