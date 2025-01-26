# Makefile for Blog Article Generator with Pipenv

PYTHON = pipenv run python
MODULE=kackle

# Default target: Show help
help:
	@echo "Usage:"
	@echo "make run-topic FROM_DATE=<YYYY-MM-DD> TO_DATE=<YYYY-MM-DD> TOPICS=<number>"
	@echo "make run-article FROM_DATE=<YYYY-MM-DD> TO_DATE=<YYYY-MM-DD> TOPICS=<number>"
	@echo "Variables:"
	@echo "  FROM_DATE: Start date for topics/articles (default: today)"
	@echo "  TO_DATE: End date for topics/articles (default: today)"
	@echo "  TOPICS: Number of topics to generate (default: 1)"
	@echo "Environment:"
	@echo "  Ensure you are using Pipenv for dependencies."

# Install dependencies using pipenv
install:
	pipenv install

# Run in topic generation mode
run-topic:
	$(PYTHON) -m $(MODULE) --mode topic --from-date $(FROM_DATE) --to-date $(TO_DATE) --topics $(TOPICS)

# Run in article generation mode
run-article:
	$(PYTHON) -m $(MODULE) --mode article --from-date $(FROM_DATE) --to-date $(TO_DATE) --topics $(TOPICS)

#python -m kackle --mode article --historical --from-date 2025-01-01 --to-date 20205-02-01

# Run default script
run-default:
	$(PYTHON) -m $(MODULE)

# Activate Pipenv shell
shell:
	pipenv shell

# Clean up any temporary files if needed
clean:
	@echo "No cleanup tasks defined."

# Variables with default values
FROM_DATE ?= $(shell date +%Y-%m-%d)
TO_DATE ?= $(shell date +%Y-%m-%d)
TOPICS ?= 1
