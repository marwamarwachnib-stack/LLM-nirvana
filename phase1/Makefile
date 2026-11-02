# Phase 1 commands (laptop or server). Run long targets inside tmux or screen.
#
#   make setup                 create the three venvs from env/*.lock (needs uv and network): analysis 3.12,
#                              code under test and Pynguin 0.34.0 on 3.10.12 with the authors' versions (decision 16)
#   make models                pull the LLMs of config main_tools into Ollama (network)
#   make datasets              rebuild the projects of the large samples (p2, p1) and their dependencies (network)
#   make validate-datasets     the authors' 144 programs against datasets/dataset_manifest.json (sha256, counts, missing)
#   make check                 what is installed / readable on this machine
#   make server-check          read-only report of the server (CPU, RAM, RAPL, Ollama, llama.cpp, models): SERVER_RUNBOOK.md
#   make verify-env            re-run the authors' stored suites, compare with their coverage reports (env/verify_environment.md)
#   make generate              Pynguin (5 seeds) + LLMs (5 repetitions), round by round, resumable (SET=small: 60 programs)
#   make execute               run every generated suite with plain pytest, 5 timed runs each, resumable
#   make results               CSVs, paper tables and figures, comparison with the paper (all rounds, and round 0 =
#                              one run per tool and program, the paper's protocol); job_status.csv lists every job
#   make all                   generate + execute + results
#   make smoke                 a few minutes, before the long run: 2-3 programs, round 0, Pynguin 30 s (runs_smoke_<set>/)
#
# One job, for an external energy meter (nothing measured inside; ENERGY=internal to measure anyway):
#   make gen-one  TOOL=cl-7b PROGRAM=cat2_functions/change REP=0
#   make exec-one TOOL=cl-7b PROGRAM=cat2_functions/change JOB=rep0      (Pynguin: TOOL=pynguin JOB=seed0)
#   gen-one does nothing for a job that is already done; exec-one adds one more run each time it is called.
#   Both run --bare (no model warm-up, no re-aggregation inside the measured command); every phase record holds
#   t_start_unix / t_end_unix, so a meter's time series can be split into load, inference, evaluation and execution.
#   Use a campaign of its own (make CAMPAIGN=<name>_ext ...): a runs folder refuses to mix energy meters.
#
# Variables: SET (small | p2 | p1, default small), CAMPAIGN (default main for small, else the set name:
#            runs_<campaign>/, results_<campaign>/; the pilot stays in runs/ and results/),
#            TOOLS (comma list, default config main_tools), ENERGY (internal | none),
#            ROUND=r (generate only round r: Pynguin seed r + LLM repetition r; e.g. ROUND=0 first),
#            HARNESS=1 (p1: prepare each failing module's import with harness/p1/<program>/conftest.py; runs_p1_harness/).
# The large samples: make datasets, then make all SET=p2 (and SET=p1).
#
# Pynguin version comparison (VERSION_COMPARISON_PLAN.md; the current venvs and locks are not touched):
#   make setup-candidate       INSTALLS (approval needed): .venv-run-cov727 (coverage 7.2.7) and .venv-pynguin-033
#   make verify-env-candidate  the authors' stored suites re-run with coverage 7.2.7 -> env/candidates/
#   make vercmp-a / vercmp-b   Pynguin on the small set, seeds 0-4 (VERCMP_REP=0: seed 0 only), current / candidate
#   make vercmp-report         results_vercmp/version_comparison.md
#
# Full-dataset pipeline (PIPELINE.md; scripts/pipeline.py, config/pipeline.yaml). Energy is NOT measured (--energy
# none: wall time and Unix timestamps per phase). Without GO=1 the experimental stages B, C, E only print their commands.
#   make pipeline-inventory                    A  verify the programs of every set, write pipeline_inventory/<id>/
#   make pipeline-plan     SET=small           every stage's exact commands for one set, in order (runs nothing)
#   make pipeline-pynguin  SET=small GO=1      B  Pynguin: EXP=paper_reproduction (default, round 0) | repeated_runs
#   make pipeline-llm      SET=small GO=1      C  local LLMs: EXP=local_llm_adaptation (default, round 0) | repeated_runs
#   make pipeline-execute  SET=small GO=1      E  timed plain-pytest runs of finished suites (EXP= one experiment; default all)
#   make pipeline-quality  SET=small           D  a new results snapshot: results_pipeline_<set>/<id>/ (no experiment)
#   make pipeline-status   SET=small              expected vs finished jobs per experiment, round and tool (read-only)
#   Options: EXP=, PTOOLS= (tool subset), ROUNDS= (round subset), PROGRAMS=, EXEC_RUNS=, OUT_ROOT=, HARNESS=1 (p1 only)

SHELL := /bin/bash
PY := .venv/bin/python
HARNESS ?=
CAMPAIGN ?= $(if $(filter small,$(SET)),main,$(SET))$(if $(filter 1,$(HARNESS)),_harness,)
export PHASE1_HARNESS := $(if $(filter 1,$(HARNESS)),1,)
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

.PHONY: help setup models datasets validate-datasets check server-check verify-env smoke generate execute results all gen-one exec-one \
        setup-candidate verify-env-candidate vercmp-a vercmp-b vercmp-report \
        pipeline-inventory pipeline-plan pipeline-pynguin pipeline-llm pipeline-execute pipeline-quality pipeline-status

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

validate-datasets:
	$(PY) scripts/validate_datasets.py

check:
	@scripts/check_setup.sh

server-check:
	bash scripts/server_check.sh

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
	./run.sh $(SET) $(TOOLS_ARG) --energy $(ENERGY) $(if $(ROUND),--rep $(ROUND),)

execute:
	@mkdir -p "$(PHASE1_RUNS)"
	set -o pipefail; $(PY) -u scripts/execute.py $(SET) $(TOOLS_ARG) --energy $(ENERGY) 2>&1 | tee -a "$(PHASE1_RUNS)/console_execute_$$(date +%Y%m%d-%H%M%S).log"

results:
	$(PY) scripts/aggregate.py
	$(PY) scripts/analyze.py
	$(PY) scripts/compare_paper.py --set $(SET)
	$(PY) scripts/compare_paper.py --set $(SET) --round 0

all: generate execute results

gen-one:
	@test -n "$(TOOL)" -a -n "$(PROGRAM)" || { echo "usage: make gen-one TOOL=<tool> PROGRAM=<category>/<program> [REP=0] [ENERGY=none]"; exit 2; }
	@[ "$(TOOL)" = pynguin ] || scripts/ollama_serve.sh >/dev/null
	$(PY) scripts/run.py $(SET) --tools $(TOOL) --programs $(PROGRAM) --rep $(REP) --energy $(ONE_ENERGY) --idle-s 0 --bare

exec-one:
	@test -n "$(TOOL)" -a -n "$(PROGRAM)" -a -n "$(JOB)" || { echo "usage: make exec-one TOOL=<tool> PROGRAM=<category>/<program> JOB=<rep0|seed0> [ENERGY=none]"; exit 2; }
	$(PY) scripts/execute.py $(SET) --tools $(TOOL) --programs $(PROGRAM) --job $(JOB) --append 1 --energy $(ONE_ENERGY) --idle-s 0 --bare

CAND_RUN := $(CURDIR)/.venv-run-cov727
CAND_PYN := $(CURDIR)/.venv-pynguin-033
VERCMP_REP ?=
VERCMP_ARGS = small --tools pynguin --energy $(ENERGY) $(if $(VERCMP_REP),--rep $(VERCMP_REP),)

setup-candidate:
	uv venv --python 3.10.12 $(CAND_RUN)
	uv pip sync --python $(CAND_RUN)/bin/python env/candidates/requirements-run-cov727.lock
	uv venv --python 3.10.12 $(CAND_PYN)
	uv pip sync --python $(CAND_PYN)/bin/python env/candidates/requirements-pynguin-033.lock

verify-env-candidate:
	PHASE1_RUNNER_VENV=$(CAND_RUN) $(PY) scripts/verify_environment.py --out env/candidates/verify_environment_cov727.md

vercmp-a:
	@mkdir -p runs_vercmp_a
	set -o pipefail; PHASE1_RUNS=$(CURDIR)/runs_vercmp_a PHASE1_RESULTS=$(CURDIR)/results_vercmp_a \
	  $(PY) -u scripts/run.py $(VERCMP_ARGS) 2>&1 | tee -a runs_vercmp_a/console_$$(date +%Y%m%d-%H%M%S).log

vercmp-b:
	@test -x $(CAND_PYN)/bin/pynguin -a -x $(CAND_RUN)/bin/python || { echo "candidate venvs missing: make setup-candidate (approval needed)"; exit 2; }
	@mkdir -p runs_vercmp_b
	set -o pipefail; PHASE1_RUNNER_VENV=$(CAND_RUN) PHASE1_PYNGUIN_VENV=$(CAND_PYN) \
	  PHASE1_RUNS=$(CURDIR)/runs_vercmp_b PHASE1_RESULTS=$(CURDIR)/results_vercmp_b \
	  $(PY) -u scripts/run.py $(VERCMP_ARGS) 2>&1 | tee -a runs_vercmp_b/console_$$(date +%Y%m%d-%H%M%S).log

vercmp-report:
	$(PY) scripts/compare_versions.py --a results_vercmp_a --b results_vercmp_b --out results_vercmp

# ----------------------------------------------------------------------------- full-dataset pipeline (PIPELINE.md)
PIPE := $(PY) scripts/pipeline.py
PIPE_OPT = $(if $(OUT_ROOT),--out-root $(OUT_ROOT),) $(if $(filter 1,$(HARNESS)),--harness,)
PIPE_SEL = --set $(SET) $(if $(EXP),--experiment $(EXP),) $(if $(PTOOLS),--tools $(PTOOLS),) \
           $(if $(ROUNDS),--rounds $(ROUNDS),) $(if $(PROGRAMS),--programs $(PROGRAMS),) $(if $(filter 1,$(GO)),--go,)

pipeline-inventory:
	$(PIPE) inventory $(PIPE_OPT)

pipeline-plan:
	$(PIPE) plan --set $(SET) $(PIPE_OPT)

pipeline-pynguin:
	$(PIPE) pynguin $(PIPE_SEL) $(PIPE_OPT)

pipeline-llm:
	$(PIPE) llm $(PIPE_SEL) $(PIPE_OPT)

pipeline-execute:
	$(PIPE) execute $(PIPE_SEL) $(if $(EXEC_RUNS),--runs $(EXEC_RUNS),) $(PIPE_OPT)

pipeline-quality:
	$(PIPE) quality --set $(SET) $(PIPE_OPT)

pipeline-status:
	$(PIPE) status --set $(SET) $(PIPE_OPT)
