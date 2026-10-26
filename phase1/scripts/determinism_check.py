"""Determinism check (PLAN.md §13.10): re-send stored iteration-1 prompts under the same cold-cache protocol
and compare the answers byte for byte with the stored ones. Nothing in runs/ is changed.

    .venv/bin/python scripts/determinism_check.py [--tools dsc-6.7b,cl-7b] [--max-per-tool N] [--out NAME.csv]
        -> results/determinism.csv (one row per re-sent prompt); rerun answers -> results/determinism/
    With more finished jobs than N, a fixed random sample (seed 0) is taken, so all categories are covered.
    `identical` compares the whole answer; `code_identical` compares only the extracted test/module code,
    which is what gets scored. `first_diff_char` is where the answers part, `diff_in_code` whether that
    point lies inside a code block.
"""
import argparse
import csv
import hashlib
import random
import tempfile
from pathlib import Path

from common import RESULTS, RUNS, load_config, on_ac, read_json
from evaluate import extract_blocks
from run import chat, cold_load, ensure_ollama


def first_diff(a, b):
    return next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), None if a == b else min(len(a), len(b)))


def in_code(text, pos):
    """Inside a ``` block (an odd fence count also covers a block left open by a cut-off answer). An answer
    without fences is taken whole as code by extract_blocks, so every position in it counts as code."""
    return pos is not None and ("```" not in text or text[:pos].count("```") % 2 == 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools", default="dsc-1.3b,dsc-6.7b,cl-7b")
    ap.add_argument("--max-per-tool", type=int, default=3)
    ap.add_argument("--out", default="determinism.csv")
    args = ap.parse_args()
    cfg = load_config()
    ensure_ollama(cfg)
    rows = []
    save = RESULTS / "determinism"
    save.mkdir(parents=True, exist_ok=True)
    for tool in args.tools.split(","):
        model = cfg["llm_tools"][tool]["model"]
        dirs = [d for d in sorted(RUNS.glob(f"{tool}/*/*/rep0/iter1")) if (d / "DONE").exists()]
        if len(dirs) > args.max_per_tool:
            dirs = sorted(random.Random(0).sample(dirs, args.max_per_tool))
        for d in dirs:
            man = read_json(d / "manifest.json")
            stored = (d / "response_raw.txt").read_text()
            cold_load(cfg, model, Path(tempfile.mkdtemp(prefix="phase1_det_")))
            resp = chat(cfg, model, (d / "prompt_system.txt").read_text(), (d / "prompt_user.txt").read_text(), man["options"])
            new = resp["message"]["content"]
            h = lambda s: hashlib.sha256(s.encode()).hexdigest()[:12]  # noqa: E731
            job = str(d.parent.parent.relative_to(RUNS / tool))
            (save / f"{tool}__{job.replace('/', '__')}__{h(new)}.txt").write_text(new)
            pos = first_diff(stored, new)
            rows.append({"tool": tool, "job": job, "stored_sha": h(stored),
                         "rerun_sha": h(new), "identical": new == stored,
                         "code_identical": extract_blocks(new)[:2] == extract_blocks(stored)[:2],
                         "first_diff_char": pos, "stored_len": len(stored), "diff_in_code": in_code(stored, pos),
                         "rerun_cached_tokens": resp.get("prompt_eval_cached_count"),
                         "rerun_on_ac": on_ac(), "stored_on_ac": man.get("system_state", {}).get("ac_online"),
                         "stored_digest": man["model_info"]["digest"][:12]})
            print(rows[-1], flush=True)
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{sum(r['identical'] for r in rows)}/{len(rows)} identical, "
          f"{sum(r['code_identical'] for r in rows)}/{len(rows)} with identical code -> {RESULTS / args.out}")


if __name__ == "__main__":
    main()
