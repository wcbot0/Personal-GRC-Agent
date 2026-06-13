.PHONY: help bootstrap selftest ingest proposals show approve reject eval eval-crosswalk redteam lint policy-lint secret-scan up down seed clean _ensure_python venv

SHELL := /bin/bash
ROOT := $(CURDIR)
VENV := $(ROOT)/.venv
ifdef CI
PYTHON := python
PIP := pip
else
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
endif

help:
	@echo "Personal GRC Agent (PGA) — common targets"
	@echo "  make bootstrap     — idempotent setup (venv, deps, docker, seed, selftest, optional Hermes)"
	@echo "  make selftest      — run integration health checks"
	@echo "  make ingest FILE=   — ingest a file into memory"
	@echo "  make proposals     — list pending change proposals"
	@echo "  make show ID=      — show a change proposal"
	@echo "  make approve ID=   — approve a change proposal"
	@echo "  make reject ID= REASON= — reject a change proposal"
	@echo "  make eval          — run golden-fixture skill evals"
	@echo "  make eval-crosswalk — run csf-crosswalk scenario evals only"
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

_ensure_python:
ifndef CI
	@test -x "$(PYTHON)" || $(MAKE) venv
endif

bootstrap:
	./bootstrap.sh

selftest: _ensure_python
	"$(PYTHON)" -m spa.selftest

ingest: _ensure_python
	@test -n "$(FILE)" || (echo "Usage: make ingest FILE=path/to/file" && exit 1)
	SPA_DATA_DIR=/tmp/spa_d SPA_AUDIT_DIR=/tmp/spa_a "$(PYTHON)" -m spa.cli ingest "$(FILE)"

proposals: _ensure_python
	"$(PYTHON)" -m spa.cli proposals list

show: _ensure_python
	@test -n "$(ID)" || (echo "Usage: make show ID=cpo-id" && exit 1)
	"$(PYTHON)" -m spa.cli proposals show "$(ID)"

approve: _ensure_python
	@test -n "$(ID)" || (echo "Usage: make approve ID=cpo-id" && exit 1)
	"$(PYTHON)" -m spa.cli proposals approve "$(ID)"

reject: _ensure_python
	@test -n "$(ID)" || (echo "Usage: make reject ID=cpo-id REASON='reason'" && exit 1)
	"$(PYTHON)" -m spa.cli proposals reject "$(ID)" --reason "$(REASON)"

eval: _ensure_python
	SPA_NO_LLM=1 SPA_DATA_DIR="$${SPA_DATA_DIR:-/tmp/spa_d}" SPA_AUDIT_DIR="$${SPA_AUDIT_DIR:-/tmp/spa_a}" "$(PYTHON)" evals/run_evals.py

eval-crosswalk: _ensure_python
	SPA_NO_LLM=1 SPA_DATA_DIR="$${SPA_DATA_DIR:-/tmp/spa_d}" SPA_AUDIT_DIR="$${SPA_AUDIT_DIR:-/tmp/spa_a}" "$(PYTHON)" evals/crosswalk_eval.py

redteam: _ensure_python
	./scripts/redteam.sh

lint: policy-lint secret-scan

policy-lint: _ensure_python
	"$(PYTHON)" -m spa.lint.policy

secret-scan: _ensure_python
	"$(PYTHON)" -m spa.lint.secrets

up:
	docker compose up -d

down:
	docker compose down

seed: _ensure_python
	"$(PYTHON)" scripts/seed_brain.py

clean:
	rm -rf .venv __pycache__ spa/__pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
