.PHONY: help bootstrap selftest ingest proposals show approve reject eval redteam lint policy-lint secret-scan up down seed clean

SHELL := /bin/bash
ROOT := $(CURDIR)
VENV := $(ROOT)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:
	@echo "Security Personal Assistant — common targets"
	@echo "  make bootstrap     — idempotent setup (venv, deps, docker, seed, selftest)"
	@echo "  make selftest      — run stub + integration self-tests"
	@echo "  make ingest FILE=   — ingest a file into memory"
	@echo "  make proposals     — list pending change proposals"
	@echo "  make show ID=      — show a change proposal"
	@echo "  make approve ID=   — approve a change proposal"
	@echo "  make reject ID= REASON= — reject a change proposal"
	@echo "  make eval          — run golden-fixture skill evals"
	@echo "  make redteam       — run prompt-injection corpus"
	@echo "  make lint          — run all linters"
	@echo "  make policy-lint   — validate autonomy-policy + schemas"
	@echo "  make secret-scan   — scan repo for secrets"
	@echo "  make up / down     — start/stop docker services"

$(VENV)/bin/python:
	python3 -m venv "$(VENV)"
	"$(PIP)" install --upgrade pip
	"$(PIP)" install -e .

venv: $(VENV)/bin/python

bootstrap:
	./bootstrap.sh

selftest: venv
	"$(PYTHON)" -m spa.selftest

ingest: venv
	@test -n "$(FILE)" || (echo "Usage: make ingest FILE=path/to/file" && exit 1)
	SPA_DATA_DIR=/tmp/spa_d SPA_AUDIT_DIR=/tmp/spa_a "$(PYTHON)" -m spa.cli ingest "$(FILE)"

proposals: venv
	"$(PYTHON)" -m spa.cli proposals list

show: venv
	@test -n "$(ID)" || (echo "Usage: make show ID=cpo-id" && exit 1)
	"$(PYTHON)" -m spa.cli proposals show "$(ID)"

approve: venv
	@test -n "$(ID)" || (echo "Usage: make approve ID=cpo-id" && exit 1)
	"$(PYTHON)" -m spa.cli proposals approve "$(ID)"

reject: venv
	@test -n "$(ID)" || (echo "Usage: make reject ID=cpo-id REASON='reason'" && exit 1)
	"$(PYTHON)" -m spa.cli proposals reject "$(ID)" --reason "$(REASON)"

eval: venv
	SPA_DATA_DIR=/tmp/spa_d SPA_AUDIT_DIR=/tmp/spa_a "$(PYTHON)" evals/run_evals.py

redteam: venv
	./scripts/redteam.sh

lint: policy-lint secret-scan

policy-lint: venv
	"$(PYTHON)" -m spa.lint.policy

secret-scan: venv
	"$(PYTHON)" -m spa.lint.secrets

up:
	docker compose up -d

down:
	docker compose down

seed: venv
	"$(PYTHON)" scripts/seed_brain.py

clean:
	rm -rf .venv __pycache__ spa/__pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
