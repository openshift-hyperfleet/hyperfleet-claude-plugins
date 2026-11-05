# Each suite exposes run-tests.sh, regardless of its implementation language.
TEST_SCRIPTS := $(sort $(wildcard */tests/run-tests.sh */skills/*/scripts/tests/run-tests.sh))

.PHONY: test test-triage

# Shared entry point for local runs and the Prow unit job.
test:
	@if [ -z "$(strip $(TEST_SCRIPTS))" ]; then \
		echo "No test suites found" >&2; \
		exit 1; \
	fi
	@for script in $(TEST_SCRIPTS); do \
		echo "Running $$script..."; \
		bash "$$script" || exit 1; \
	done

test-triage:
	bash hyperfleet-work-triage/skills/open-prs/scripts/tests/run-tests.sh
