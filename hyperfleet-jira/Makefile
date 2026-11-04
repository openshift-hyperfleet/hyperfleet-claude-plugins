PYTHON ?= python3

.PHONY: test

# The same command CI runs in .github/workflows/hyperfleet-jira-tests.yml.
test:
	$(PYTHON) -m unittest discover -s tests -v
