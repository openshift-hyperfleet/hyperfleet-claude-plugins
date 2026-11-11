# CI Workflows

Run all discovered plugin test suites locally before opening a PR:

```bash
make test
```

The Makefile exposes `help` and `test`; the aggregate test target discovers each
suite's `run-tests.sh`. See [CONTRIBUTING.md](../../CONTRIBUTING.md#testing) for
the authoritative runner contract and dependencies.
To run one suite in isolation, invoke its runner directly, for example:

```bash
bash hyperfleet-jira/tests/run-tests.sh
```

There are no scheduled workflows in this directory at present.

The Prow unit job is configured separately in `openshift/release` under
`ci-operator/config/openshift-hyperfleet/hyperfleet-claude-plugins` and runs
`make test`. Until the presubmit is active, validation must be run locally.
