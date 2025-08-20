# Simple developer helpers (primarily for non-Windows)

.PHONY: help test lint diag diag-json chat daily build clean

help:
	@echo "Targets: test lint diag diag-json chat daily build clean"

test:
	pytest -q

lint:
	pre-commit run --all-files

diag:
	python -m ui.cli diag

diag-json:
	python -m ui.cli diag --json --filter version env http scheduler

chat:
	python -m ui.cli chat --once hello

daily:
	python -m ui.cli jobs daily-summary

build:
	python -m build

clean:
	rm -rf dist build *.egg-info
