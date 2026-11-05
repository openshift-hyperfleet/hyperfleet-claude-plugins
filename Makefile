.PHONY: test test-triage

# Shared entry point for local runs and the Prow unit job.
test: test-triage

test-triage:
	bash hyperfleet-work-triage/skills/open-prs/scripts/tests/run-tests.sh
