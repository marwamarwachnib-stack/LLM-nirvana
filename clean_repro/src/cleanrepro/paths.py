"""Fixed locations used by every module of the clean reproduction."""
from __future__ import annotations

import os
from pathlib import Path

CLEAN = Path(__file__).resolve().parents[2]          # clean_repro/
REPO = CLEAN.parent                                   # repository root (original materials, read-only)
CR_HOME = Path(os.environ.get("CR_HOME", "/opt/clean_repro"))   # heavy files, outside git
WORK = CR_HOME / "work"                               # scratch sandboxes (never inside the repository)
CACHE = CR_HOME / "cache"
ENVS = CR_HOME / "conda" / "envs"

SMALL = REPO / "0_100 LOC"
P1 = REPO / "100_300 LOC p1"
P2 = REPO / "100_300 LOC p2"
P2_GPT = P2 / "ChatGPT coverage"
P2_PYN = P2 / "pynguin coverage"

BENCH = CLEAN / "benchmark"
DATA = CLEAN / "data"
RESULTS = CLEAN / "results"
RUNS = CLEAN / "runs"
CONFIG = CLEAN / "config"

SMALL_DIRS = {1: SMALL / "cat1_scripts", 2: SMALL / "cat2_functions", 3: SMALL / "cat3_classes"}
P1_DIRS = {1: P1 / "cat1", 2: P1 / "cat2", 3: P1 / "cat3"}


def env_python(name: str) -> Path:
    return ENVS / name / "bin" / "python"


def rel(p: Path) -> str:
    """Path relative to the repository root, as stored in CSV files."""
    return str(Path(p).resolve().relative_to(REPO))
