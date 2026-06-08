# CI Workflows

## Open PRs Digest

**File:** `open-prs-digest.yml`

Runs the `/open-prs --slack` skill every weekday via `claude-code-action` and posts the prioritized PR review queue to Slack.

### Setup

#### GCP Service Account

The workflow authenticates to Vertex AI using a service account key. You need:

1. A GCP project with Vertex AI enabled (the team uses `itpc-gcp-hcm-pe-eng-claude`)
2. A service account with `roles/aiplatform.user` permission
3. A JSON key for the service account

Create the key and store its contents as the `GCP_SA_KEY` secret:

```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=openshift-ci-github-action@itpc-gcp-hcm-pe-eng-claude.iam.gserviceaccount.com

# Copy the JSON contents into the GCP_SA_KEY secret, then delete the file
rm key.json
```

#### GitHub Fine-Grained PAT

The `/open-prs` skill queries PRs across all repos in `openshift-hyperfleet`. The default `GITHUB_TOKEN` is scoped to this repo only, so a fine-grained PAT with org-wide read access is required.

1. Go to [GitHub → New fine-grained token](https://github.com/settings/personal-access-tokens/new)
2. **Token name**: `hyperfleet-open-prs-digest`
3. **Resource owner**: select `openshift-hyperfleet`
4. **Repository access**: All repositories
5. **Permissions** → Repository permissions:
   - Contents: **Read-only**
   - Pull requests: **Read-only**
   - Metadata: **Read-only** (selected automatically)
6. Click **Generate token** → copy the token
7. Save it as the `GH_TOKEN_ORG_READ` secret in the repo

#### Slack Incoming Webhooks

Create two webhooks:

1. **Team channel** — for the daily digest
2. **Personal/ops channel** — for error notifications

Create webhooks in the [HyperFleet Slack App](https://api.slack.com/apps/A0B3FC58FPE/incoming-webhooks).

### Required Secrets

Configure these in the repo's Settings → Secrets and variables → Actions:

| Secret | Description | Example |
|--------|-------------|---------|
| `GCP_SA_KEY` | GCP service account key JSON | (see GCP Service Account section above) |
| `ANTHROPIC_VERTEX_PROJECT_ID` | GCP project with Vertex AI | `itpc-gcp-hcm-pe-eng-claude` |
| `GH_TOKEN_ORG_READ` | GitHub PAT with repo read access across `openshift-hyperfleet` | ([generate fine-grained token](https://github.com/settings/personal-access-tokens/new) — owner: `openshift-hyperfleet`, permissions: Contents + Pull requests + Metadata read-only) |
| `JIRA_API_TOKEN` | JIRA Personal Access Token | (generate at [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)) |
| `JIRA_AUTH_LOGIN` | JIRA account email | `user@redhat.com` |
| `SLACK_WEBHOOK_URL` | Webhook for the team channel | `https://hooks.slack.com/services/T.../B.../...` |
| `SLACK_WEBHOOK_URL_ERRORS` | Webhook for error notifications | `https://hooks.slack.com/services/T.../B.../...` |

### Manual Trigger

Go to Actions → Open PRs Digest → Run workflow, or:

```bash
gh workflow run open-prs-digest.yml
```

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| GCP auth fails | SA key invalid or expired | Generate a new key and update `GCP_SA_KEY` |
| JIRA data missing | Token expired | Generate a new PAT and update `JIRA_API_TOKEN` |
| Slack post returns non-200 | Webhook revoked | Recreate the webhook and update `SLACK_WEBHOOK_URL` |
| Claude times out | Too many PRs / max-turns too low | Increase `--max-turns` in `claude_args` |
