# Phase 1 commands (laptop or server). Run long targets inside tmux or screen.
#
#   make setup                 create the three venvs from env/*.lock (needs uv and network): analysis 3.12,
#                              code under test and Pynguin 0.34.0 on 3.10.12 with the authors' versions (decision 16)
#   make models                pull the LLMs of config main_tools into Ollama (network)
#   make datasets              rebuild the projects of the large samples (p2, p1) and their dependencies (network)
#   make check                 what is installed / readable on this machine
#   make verify-env            re-run the authors' stored suites, compare with their coverage reports (env/verify_environment.md)
#   make generate              Pynguin (5 seeds) + LLMs (5 repetitions), round by round, resumable (SET=small: 60 programs)
#   make execute               run every generated suite with plain pytest, 5 timed runs each, resumable
#   make results               CSVs, paper tables and figures, comparison with the paper
#   make all                   generate + execute + results
#   make smoke                 a few minutes, before the long run: 2-3 programs, round 0, Pynguin 30 s (runs_smoke_<set>/)
#
# One job, for an external energy meter (nothing measured inside; ENERGY=internal to measure anyway):
#   make gen-one  TOOL=cl-7b PROGRAM=cat2_functions/change REP=0
#   make exec-one TOOL=cl-7b PROGRAM=cat2_functions/change JOB=rep0      (Pynguin: TOOL=pynguin JOB=seed0)
#   gen-one does nothing for a job that is already done; exec-one adds one more run each time it is called.
#
# Variables: SET (small | p2 | p1, default small), CAMPAIGN (default main for small, else the set name:
#            runs_<campaign>/, results_<campaign>/; the pilot stays in runs/ and results/),
#            TOOLS (comma list, default config main_tools), ENERGY (internal | none).
# The large samples: make datasets, then make all SET=p2 (and SET=p1).

SHELL := /bin/bash
PY := .venv/bin/python
CAMPAIGN ?= $(if $(filter small,$(SET)),main,$(SET))
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

.PHONY: help setup models datasets check verify-env smoke generate execute results all gen-one exec-one

help:
	@sed -n '1,/^$$/p' Makefile | sed 's/^# \{0,1\}//'

setup:
	uv venv --clear --python 3.12 .venv
	uv pip sync --python .venv/bin/python env/requirements-venv.lock
	uv venv --clear --python 3.10.12 .venv-run
	uv pip sync --python .venv-run/bin/python env/requirements-run.lock
	uv venv --clear --python 3.10.12 .venv-pynguin
	uv pip sync --python .venv-pynguin/bin/python env/requirements-venv-pynguin.lock

models:
	scripts/ollama_serve.sh
	@for m in $(MODELS); do echo "pull $$m"; "$$(scripts/ollama_bin.sh)" pull "$$m" || exit 1; done

datasets:
	$(PY) scripts/prepare_datasets.py p2
	$(PY) scripts/prepare_datasets.py p1

check:
	@scripts/check_setup.sh

verify-env:
	$(PY) scripts/verify_environment.py

SMOKE_small := cat1_scripts/FizzBuzz,cat2_functions/change,cat3_classes/bank-account
SMOKE_p2 := cat2_functions/sample2,cat3_classes/sample24
SMOKE_p1 := cat2_functions/cat2_s14,cat3_classes/cat3_s2
smoke: export PHASE1_RUNS := $(CURDIR)/runs_smoke_$(SET)
smoke: export PHASE1_RESULTS := $(CURDIR)/results_smoke_$(SET)
smoke:
	./run.sh $(SET) $(TOOLS_ARG) --programs $(SMOKE_$(SET)) --rep 0 --pynguin-time 30 --idle-s 10 --energy $(ENERGY)
	$(PY) scripts/execute.py $(SET) $(TOOLS_ARG) --programs $(SMOKE_$(SET)) --runs 1 --idle-s 0 --energy $(ENERGY)
	$(PY) scripts/aggregate.py && $(PY) scripts/analyze.py && $(PY) scripts/compare_paper.py --set $(SET)
	@echo "smoke test done: $$PHASE1_RESULTS/paper_comparison.md"

generate:
	./run.sh $(SET) $(TOOLS_ARG) --energy $(ENERGY)

execute:
	@mkdir -p "$(PHASE1_RUNS)"
	set -o pipefail; $(PY) -u scripts/execute.py $(SET) $(TOOLS_ARG) --energy $(ENERGY) 2>&1 | tee -a "$(PHASE1_RUNS)/console_execute_$$(date +%Y%m%d-%H%M%S).log"

results:
	$(PY) scripts/aggregate.py
	$(PY) scripts/analyze.py
	$(PY) scripts/compare_paper.py --set $(SET)

all: generate execute results

gen-one:
	@test -n "$(TOOL)" -a -n "$(PROGRAM)" || { echo "usage: make gen-one TOOL=<tool> PROGRAM=<category>/<program> [REP=0] [ENERGY=none]"; exit 2; }
	@[ "$(TOOL)" = pynguin ] || scripts/ollama_serve.sh >/dev/null
	$(PY) scripts/run.py $(SET) --tools $(TOOL) --programs $(PROGRAM) --rep $(REP) --energy $(ONE_ENERGY) --idle-s 0

exec-one:
	@test -n "$(TOOL)" -a -n "$(PROGRAM)" -a -n "$(JOB)" || { echo "usage: make exec-one TOOL=<tool> PROGRAM=<category>/<program> JOB=<rep0|seed0> [ENERGY=none]"; exit 2; }
	$(PY) scripts/execute.py $(SET) --tools $(TOOL) --programs $(PROGRAM) --job $(JOB) --append 1 --energy $(ONE_ENERGY) --idle-s 0
