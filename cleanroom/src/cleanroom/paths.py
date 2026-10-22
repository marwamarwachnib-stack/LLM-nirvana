"""Fixed locations of the frozen snapshot and of clean-room outputs."""
from __future__ import annotations

from pathlib import Path

CLEANROOM = Path(__file__).resolve().parents[2]
REPO_ROOT = CLEANROOM.parent

# Frozen benchmark snapshot (decision 1). Equivalence with the upstream
# Shreya20542/LLM-nirvana repository is NOT verified.
SNAPSHOT_COMMIT = "e330b23581ed26d8b4983bed8766f012f79287ed"

# Top-level entries of the repository that are not part of the original snapshot.
NON_ORIGINAL_TOP_LEVEL = frozenset({".git", "cleanroom"})

BENCHMARK_DIR = CLEANROOM / "benchmark"
INVENTORY_TSV = BENCHMARK_DIR / "originals_sha256.tsv"
SHA256SUMS = BENCHMARK_DIR / "originals.SHA256SUMS"
INVENTORY_META = BENCHMARK_DIR / "originals_inventory_meta.json"
MANIFEST_CSV = BENCHMARK_DIR / "manifest.csv"
REPORTS_DIR = CLEANROOM / "reports"
LOGS_DIR = CLEANROOM / "logs"
