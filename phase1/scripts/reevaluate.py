"""Re-score stored test suites with the current evaluator (no new generation).

    .venv/bin/python scripts/reevaluate.py pynguin
        Finished Pynguin runs whose metrics.json has an older evaluator_version are re-evaluated in place.
        The previous metrics are kept as metrics_evaluator_v<k>.json; generation energy and logs are untouched.

    .venv/bin/python scripts/reevaluate.py llm-iter1 <runs_dir> <out_dir>
        Iteration 1 of every LLM job under <runs_dir> (e.g. an archived pilot) is re-normalized from its raw
        test file and re-evaluated in a copy under <out_dir>; one CSV row per job -> <out_dir>/iter1_rescored.csv.
        Only iteration 1 can be re-scored this way: later prompts depended on the old scores.
"""
import argparse
import csv
import shutil
import sys
from pathlib import Path

from common import RUNS, atomic_write_json, load_config, read_json
from evaluate import EVALUATOR_VERSION, evaluate, normalize_imports


def pynguin(cfg):
    n = 0
    for d in sorted(RUNS.glob("pynguin/*/*/seed*")):
        if not (d / "DONE").exists():
            continue
        m = read_json(d / "metrics.json")
        old = m.get("evaluator_version", 1)
        if old >= EVALUATOR_VERSION:
            continue
        shutil.copy(d / "metrics.json", d / f"metrics_evaluator_v{old}.json")
        new = evaluate(d / "work", ["test_example.py"], cfg)
        atomic_write_json(d / "metrics.json", {**m, **new, "reevaluated_from_version": old})
        print(f"  {d.relative_to(RUNS)}: stmt {m['coverage']['stmt_cov']} -> {new['coverage']['stmt_cov']}, "
              f"incorrect {m['assertions'].get('incorrect_pct')} -> {new['assertions'].get('incorrect_pct')}")
        n += 1
    print(f"{n} Pynguin runs re-evaluated (evaluator v{EVALUATOR_VERSION})")


def llm_iter1(cfg, runs_dir, out_dir):
    rows = []
    for job in sorted(Path(runs_dir).glob("*/*/*/rep0/job.json")):
        j = read_json(job)
        it = job.parent / "iter1"
        if j.get("status") != "done" or not (it / "DONE").exists():
            continue
        src = it / "work"
        w = Path(out_dir) / j["tool"] / j["category"] / j["program"]
        if w.exists():
            shutil.rmtree(w)
        w.mkdir(parents=True)
        module = (src / "example.py").read_text()  # refactored Cat-1 module if the LLM gave one
        (w / "example.py").write_text(module)
        raw = (src / "test_example_i1.raw.py").read_text()
        norm, changes = normalize_imports(raw, module)
        (w / "test_example_i1.raw.py").write_text(raw)
        (w / "test_example_i1.py").write_text(norm)
        atomic_write_json(w / "import_changes.json", changes)
        old = read_json(it / "metrics.json")
        m = evaluate(w, ["test_example_i1.py"], cfg)
        c, t, a = m["coverage"], m["tests"], m["assertions"]
        rows.append({"tool": j["tool"], "category": j["category"], "program": j["program"],
                     "stmt_cov_v1": old["coverage"]["stmt_cov"], "branch_cov_v1": old["coverage"]["branch_cov"],
                     "incorrect_pct_v1": old["assertions"].get("incorrect_pct"),
                     "stmt_cov": c["stmt_cov"], "branch_cov": c["branch_cov"], "n_tests": t["n_tests"], "passed": t["passed"],
                     "incorrect_pct": a.get("incorrect_pct"),
                     "imports_renamed": sum(x["rule"] == "renamed-module" for x in changes),
                     "import_added": any(x["rule"] == "added-missing-import" for x in changes),
                     "collection_error": m["errors"]["n_collection_error"] > 0,
                     "evaluator_version": EVALUATOR_VERSION})
    out = Path(out_dir) / "iter1_rescored.csv"
    with open(out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"{len(rows)} LLM iteration-1 suites -> {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["pynguin", "llm-iter1"])
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args()
    cfg = load_config()
    if args.what == "pynguin":
        pynguin(cfg)
    else:
        if len(args.paths) != 2:
            sys.exit("llm-iter1 needs <runs_dir> <out_dir>")
        llm_iter1(cfg, *args.paths)


if __name__ == "__main__":
    main()
