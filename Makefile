PYTHON ?= python3
export PYTHON

.PHONY: test test-jira test-triage

# Shared entry point for local runs and the Prow unit job.
test: test-jira test-triage

test-jira:
	"$$PYTHON" -m unittest discover -s hyperfleet-jira/tests -v

test-triage:
	bash hyperfleet-work-triage/skills/open-prs/scripts/tests/run-tests.sh
