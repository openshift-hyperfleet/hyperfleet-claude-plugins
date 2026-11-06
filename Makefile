.PHONY: help test lint

help: ## Show available targets without running them
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

lint: ## Lint Markdown and YAML
	@bash hack/markdownlint.sh
	@bash hack/yamllint.sh

# Shared entry point for local runs and the Prow unit job.
test: ## Run all discovered test suites
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
