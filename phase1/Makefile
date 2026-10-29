# Phase 1 commands (laptop or server). Run long targets inside tmux or screen.
#
#   make setup                 create the two venvs from env/*.lock (needs uv and network)
#   make models                pull the LLMs of config main_tools into Ollama (network)
#   make check                 what is installed / readable on this machine
#   make generate              Pynguin (5 seeds) + LLMs (5 repetitions) on the 60 programs, round by round, resumable
#   make execute               run every generated suite with plain pytest, 5 timed runs each, resumable
#   make results               CSVs, paper tables and figures, comparison with the paper
#   make all                   generate + execute + results
#
# One job, for an external energy meter (nothing measured inside; ENERGY=internal to measure anyway):
#   make gen-one  TOOL=cl-7b PROGRAM=cat2_functions/change REP=0
#   make exec-one TOOL=cl-7b PROGRAM=cat2_functions/change JOB=rep0      (Pynguin: TOOL=pynguin JOB=seed0)
#   gen-one does nothing for a job that is already done; exec-one adds one more run each time it is called.
#
# Variables: CAMPAIGN (default main: runs_main/, results_main/; the pilot stays in runs/ and results/),
#            SET (default small), TOOLS (comma list, default config main_tools), ENERGY (internal | none).

SHELL := /bin/bash
PY := .venv/bin/python
CAMPAIGN ?= main
SET ?= small
TOOLS ?=
ENERGY ?= internal
REP ?= 0
export PHASE1_RUNS := $(CURDIR)/runs_$(CAMPAIGN)
export PHASE1_RESULTS := $(CURDIR)/results_$(CAMPAIGN)
TOOLS_ARG := $(if $(TOOLS),--tools $(TOOLS),)
# one-job targets default to ENERGY=none (an external meter wraps them) unless ENERGY is given on the command line
ONE_ENERGY := $(if $(filter command line,$(origin ENERGY)),$(ENERGY),none)
MODELS = $$($(PY) -c 'import sys; sys.path.insert(0, "scripts"); from common import load_config; c = load_config(); print(*[c["llm_tools"][t]["model"] for t in c["main_tools"] if t != "pynguin"])')

.PHONY: help setup models check generate execute results all gen-one exec-one

help:
	@sed -n '1,/^$$/p' Makefile | sed 's/^# \{0,1\}//'

setup:
	uv venv --python 3.12 .venv
	uv pip sync --python .venv/bin/python env/requirements-venv.lock
	uv venv --python 3.12 .venv-pynguin
	uv pip sync --python .venv-pynguin/bin/python env/requirements-venv-pynguin.lock

models:
	scripts/ollama_serve.sh
	@for m in $(MODELS); do echo "pull $$m"; "$$(scripts/ollama_bin.sh)" pull "$$m" || exit 1; done

check:
	@scripts/check_setup.sh

generate:
	./run.sh $(SET) $(TOOLS_ARG) --energy $(ENERGY)

execute:
	@mkdir -p "$(PHASE1_RUNS)"
	set -o pipefail; $(PY) -u scripts/execute.py $(SET) $(TOOLS_ARG) --energy $(ENERGY) 2>&1 | tee -a "$(PHASE1_RUNS)/console_execute_$$(date +%Y%m%d-%H%M%S).log"

results:
	$(PY) scripts/aggregate.py
	$(PY) scripts/analyze.py
	$(PY) scripts/compare_paper.py

all: generate execute results

gen-one:
	@test -n "$(TOOL)" -a -n "$(PROGRAM)" || { echo "usage: make gen-one TOOL=<tool> PROGRAM=<category>/<program> [REP=0] [ENERGY=none]"; exit 2; }
	@[ "$(TOOL)" = pynguin ] || scripts/ollama_serve.sh >/dev/null
	$(PY) scripts/run.py $(SET) --tools $(TOOL) --programs $(PROGRAM) --rep $(REP) --energy $(ONE_ENERGY) --idle-s 0

exec-one:
	@test -n "$(TOOL)" -a -n "$(PROGRAM)" -a -n "$(JOB)" || { echo "usage: make exec-one TOOL=<tool> PROGRAM=<category>/<program> JOB=<rep0|seed0> [ENERGY=none]"; exit 2; }
	$(PY) scripts/execute.py $(SET) --tools $(TOOL) --programs $(PROGRAM) --job $(JOB) --append 1 --energy $(ONE_ENERGY) --idle-s 0
