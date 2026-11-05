.PHONY: test

# Shared entry point for local runs and the Prow unit job.
test:
	@found=0; \
	for script in */tests/run-tests.sh */skills/*/scripts/tests/run-tests.sh; do \
		[ -f "$$script" ] || continue; \
		found=1; \
		printf 'Running %s...\n' "$$script"; \
		bash "$$script" || exit 1; \
	done; \
	if [ "$$found" -eq 0 ]; then \
		echo "No test suites found" >&2; \
		exit 1; \
	fi
