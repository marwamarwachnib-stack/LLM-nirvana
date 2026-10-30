"""Phase 1 results next to the numbers of Bhatia et al. (2024), arXiv 2312.10622v2, and the authors' stored files.

    .venv/bin/python scripts/compare_paper.py [--set small|p2|p1]

Reads results/jobs.csv, iterations.csv and overlap.csv (of the campaign in PHASE1_RESULTS) and the authors' files.
Writes results/paper_comparison.md and results/paper_comparison.csv.

Dataset behind each paper table (repository READMEs; the audit of the stored files reproduces Table 2 and its
p-values from p2 exactly):
  Table 1  0-100 LOC                  -> --set small (also: the authors' stored Pynguin suites, per program)
  Table 2  100-300 LOC p2, 41 samples -> --set p2 (also: the authors' per-sample coverage of both tools, Fig. 4)
  Table 5  p2 (missed statements)     -> --set p2
  Table 3  100-300 LOC p1             -> --set p1
  Table 4  not stated in the paper    -> shown with every set (Cat 1: refactored modules only, as in §3.2.3)
The paper's "Avg Branch Coverage" is coverage.py's Cover column with --branch (statements + branches together),
the column of the authors' branch_coverage.txt; it is compared with our stmt_branch_cov.
LLM repetitions and Pynguin seeds are averaged per program first; the t-test is Student's, as in the paper.
"""
import argparse
import csv
import json
import re

import pandas as pd
from scipy import stats

from common import PHASE1, REPO, RESULTS
from xcheck_stored import stored

CAT = {"cat1_scripts": "cat1", "cat2_functions": "cat2", "cat3_classes": "cat3"}
# Table 1: (ChatGPT, Pynguin) for statement, then branch ("Cover" with --branch)
T1 = {"cat1 original": ((0, 0), (0, 0)), "cat1 refactored": ((97.45, 0), (96.85, 0)),
      "cat2": ((93.26, 90.3), (91.68, 90.1)), "cat3": ((91.55, 97), (89.5, 96.15))}
T1_P = {"cat2": (0.631, 0.807), "cat3": (0.218, 0.193)}  # ChatGPT vs Pynguin, statement / branch
# Table 2: (ChatGPT, Pynguin) for statement, then branch; "Average on all 40 samples" (the arithmetic needs 41)
T2 = {"cat2": ((77.44, 88.77), (74.77, 86.22)), "cat3": ((77.4, 79.6), (73, 76.15)), "all": ((77.43, 81.63), (73.39, 78.36))}
T2_P = {"cat2": (0.169, 0.195), "cat3": (0.677, 0.580)}
T3_COLS = ("iter1", "iter5_or_last", "best", "best_minus_least", "median_iters")
T3 = {"cat1": (56.833, 56.833, 56.833, 0, 1), "cat2": (63.6, 90.5, 91.55, 27.95, 4), "cat3": (72.45, 87.7, 87.7, 15.25, 4)}
T4_COLS = ("all_incorrect", "assertion_error", "try_except", "runtime")
T4 = {"cat1": (57.75, 86.93, 0, 13.07), "cat2": (39.4, 78.30, 2.68, 19.02), "cat3": (27.67, 70.96, 3.66, 25.38)}
T5 = {"intersecting_missed": 17.78, "union_missed": 50.33, "minimum_missed": 20.29, "minimum_covered": 2.51,
      "maximum_covered": 31.64}
P2 = REPO / "100_300 LOC p2"
P2_DEV_TESTS = {"sample9", "sample10", "sample11", "sample12"}  # the "Pynguin" folder holds the project's own tests


def fmt(v, nd=2):
    return "—" if v is None or pd.isna(v) else f"{v:.{nd}f}"


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def row_label(r):
    cat = CAT.get(r["category"], r["category"])
    if cat == "cat1":
        return "cat1 refactored" if str(r.get("refactored_module")) == "True" else "cat1 original"
    return cat


def student(a, b):
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    return stats.ttest_ind(a, b).pvalue if len(a) >= 2 and len(b) >= 2 else None


class Report:
    def __init__(self, title):
        self.md, self.long = [f"# {title}", ""], []

    def add(self, table, row, metric, source, tool, value, n=None):
        self.long.append({"table": table, "row": row, "metric": metric, "source": source, "tool": tool,
                          "value": value, "n": n})


# ----------------------------------------------------------------------------- the authors' p2 files

def expand(missing):
    out = set()
    for part in (missing or "").replace(" ", "").split(","):
        if "->" in part or not part:  # branch arcs (a->b) are not statements
            continue
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


def report_row(path, module):
    """(stmts, miss, cover %, missing statement lines) of the module's row in a coverage.py text report."""
    if not path or not path.exists():
        return None
    rows = [ln.split() for ln in path.read_text().splitlines()]
    rows = [c for c in rows if c and c[0].split("/")[-1] == f"{module}.py"]
    if not rows:
        return None
    cols = min(rows, key=lambda c: len(c[0]))  # the module itself before same-named files deeper in the package
    pct = next(i for i, c in enumerate(cols) if c.endswith("%"))
    return {"stmts": int(cols[1]), "cover": float(cols[pct].rstrip("%")), "missing": expand(" ".join(cols[pct + 1:]))}


def pick(folder, kind):
    """The authors' report file: names vary (statement_coverage_ssl.txt, statement_coverage.txt); sample38 also
    has an older run (*_old), not used."""
    files = sorted(folder.glob(f"{kind}_coverage*.txt"), key=lambda f: ("_old" in f.name, f.name))
    return files[0] if files else None


def authors_p2():
    """Per sample: the authors' ChatGPT and Pynguin statement / Cover(--branch) values and missed statements."""
    man = json.loads((PHASE1 / "datasets" / "p2" / "manifest.json").read_text())
    out = {}
    for name, e in man["programs"].items():
        mod, pdir, gdir = e["module"], P2 / "pynguin coverage" / name, P2 / "ChatGPT coverage" / name
        ps, pb = report_row(pick(pdir, "statement"), mod), report_row(pick(pdir, "branch"), mod)
        gs, gb = report_row(gdir / "statement_coverage.txt", mod), report_row(gdir / "branch_coverage.txt", mod)
        out[name] = {"module": mod, "category": e["category"],
                     "gpt_stmt": gs and gs["cover"], "gpt_branch": gb and gb["cover"], "gpt_missed": gs and gs["missing"],
                     "pyn_stmt": ps and ps["cover"], "pyn_branch": pb and pb["cover"], "pyn_missed": ps and ps["missing"]}
    return out


# ----------------------------------------------------------------------------- sections

def section_table1(rep, per, tools, llms):
    rep.md += ["## Table 1: coverage, 0-100 LOC (iteration 1)", ""]
    for mi, (metric, label) in enumerate((("stmt_cov", "statement"), ("stmt_branch_cov", "branch (Cover with --branch)"))):
        rows = []
        for r, vals in T1.items():
            cells = [r, fmt(vals[mi][0]), fmt(vals[mi][1])]
            for t in tools:
                s = per[(per.tool == t) & (per.row == r)][metric].dropna()
                cells.append(f"{fmt(s.mean())} (n={len(s)})" if len(s) else "—")
                rep.add("1", r, metric, "ours", t, s.mean() if len(s) else None, len(s))
            for tool, v in zip(("chatgpt", "pynguin"), vals[mi]):
                rep.add("1", r, metric, "paper", tool, v)
            rows.append(cells)
        rep.md += [f"**{label}**", "", md_table(["row", "paper ChatGPT", "paper Pynguin"] + [f"ours {t}" for t in tools], rows), ""]
    rows = []
    for cat, ps in T1_P.items():
        for t in llms:
            a, b = (per[(per.tool == x) & (per.row == cat)] for x in (t, "pynguin"))
            cells = [cat, t]
            for metric, paper_p in zip(("stmt_cov", "stmt_branch_cov"), ps):
                p = student(a[metric], b[metric])
                cells += [fmt(paper_p, 3), fmt(p, 3)]
                rep.add("1 t-test", cat, metric, "ours", f"{t} vs pynguin", p)
            rows.append(cells)
    rep.md += ["**Student t-test p-values (threshold 0.05)**", "",
               md_table(["row", "LLM vs Pynguin", "paper p stmt", "ours p stmt", "paper p branch", "ours p branch"], rows), ""]


def section_stored_small(rep, jobs):
    rows, diffs = [], []
    py = jobs[jobs.tool == "pynguin"].groupby(["category", "program"])["stmt_cov"].agg(["mean", "min", "max"])
    for (cat, prog), r in py.iterrows():
        s = stored(REPO / "0_100 LOC" / cat / prog / "line_coverage.txt")
        if not s:
            continue
        theirs = int(s[3].rstrip("%"))
        diffs.append(r["mean"] - theirs)
        rows.append([f"{cat}/{prog}", theirs, fmt(r["mean"]), f"{fmt(r['min'], 0)}–{fmt(r['max'], 0)}"])
    if rows:
        close = sum(abs(d) <= 1 for d in diffs)
        rep.md += ["## The authors' stored Pynguin suites vs our Pynguin runs (statement coverage, 0-100 LOC)", "",
                   f"{len(rows)} programs; ours within 1 point of theirs on {close}; mean difference (ours − theirs) "
                   f"{sum(diffs) / len(diffs):+.2f} points.", "",
                   md_table(["program", "authors (one run)", "ours (mean over seeds)", "ours min–max"], rows), ""]


def section_table2(rep, per, tools, llms, auth):
    """Table 2 on the authors' 41 samples (the ones with ChatGPT coverage), and per sample (Fig. 4)."""
    a41 = {n for n, a in auth.items() if a["gpt_stmt"] is not None}
    rep.md += ["## Table 2: coverage, 100-300 LOC p2 (iteration 1)", "",
               f"Rows over the authors' {len(a41)} samples with ChatGPT coverage (the paper's caption says 40; its means "
               "need 41). 'authors' files' = recomputed from the coverage reports in the repository (the paper's Fig. 4 "
               "differs from them on s5, s25, s31). Categories: any class → Cat 3 (the split that reproduces Table 2).", ""]
    af = pd.DataFrame.from_dict(auth, orient="index")
    for mi, (metric, a_g, a_p, label) in enumerate((("stmt_cov", "gpt_stmt", "pyn_stmt", "statement"),
                                                    ("stmt_branch_cov", "gpt_branch", "pyn_branch", "branch (Cover with --branch)"))):
        rows = []
        for r, vals in T2.items():
            sel = af.loc[sorted(a41)]
            if r != "all":
                sel = sel[sel.category.map(CAT) == r]
            cells = [r, fmt(vals[mi][0]), fmt(vals[mi][1]), fmt(sel[a_g].mean()), fmt(sel[a_p].mean())]
            for t in tools:
                s = per[(per.tool == t) & per.program.isin(sel.index)][metric].dropna()
                cells.append(f"{fmt(s.mean())} (n={len(s)})" if len(s) else "—")
                rep.add("2", r, metric, "ours", t, s.mean() if len(s) else None, len(s))
            rep.add("2", r, metric, "authors' files", "chatgpt", sel[a_g].mean(), len(sel))
            rep.add("2", r, metric, "authors' files", "pynguin", sel[a_p].mean(), len(sel))
            rows.append(cells)
        rep.md += [f"**{label}**", "", md_table(["row", "paper ChatGPT", "paper Pynguin", "authors' files ChatGPT",
                                                 "authors' files Pynguin"] + [f"ours {t}" for t in tools], rows), ""]
    rows = []
    for cat, ps in T2_P.items():
        sel = [n for n in a41 if CAT.get(auth[n]["category"]) == cat]
        for t in llms:
            a, b = (per[(per.tool == x) & per.program.isin(sel)] for x in (t, "pynguin"))
            cells = [cat, t]
            for metric, paper_p in zip(("stmt_cov", "stmt_branch_cov"), ps):
                p = student(a[metric], b[metric])
                cells += [fmt(paper_p, 3), fmt(p, 3)]
                rep.add("2 t-test", cat, metric, "ours", f"{t} vs pynguin", p)
            rows.append(cells)
    rep.md += ["**Student t-test p-values (threshold 0.05)**", "",
               md_table(["row", "LLM vs Pynguin", "paper p stmt", "ours p stmt", "paper p branch", "ours p branch"], rows), ""]
    # Fig. 4, per sample
    rows = []
    for n in sorted(auth, key=lambda x: int(x[6:])):
        a = auth[n]
        cells = [n, a["module"], CAT.get(a["category"]), fmt(a["gpt_stmt"], 0),
                 fmt(a["pyn_stmt"], 0) + (" (dev. tests)" if n in P2_DEV_TESTS else "")]
        for t in tools:
            s = per[(per.tool == t) & (per.program == n)]["stmt_cov"]
            cells.append(fmt(s.mean(), 1) if len(s) else "—")
        rows.append(cells)
    rep.md += ["## Fig. 4: statement coverage per sample, p2 (iteration 1)", "",
               "'dev. tests': the authors' Pynguin folder holds the project's own tests, not Pynguin's (s9–s12).", "",
               md_table(["sample", "module", "cat", "authors ChatGPT", "authors Pynguin"] + [f"ours {t}" for t in tools], rows), ""]


def section_table5(rep, auth):
    """Table 5 / Fig. 7: missed-statement overlap, with the paper's definitions (averages over samples)."""
    def summary(inter, union, miss_a, miss_b):
        mi = min(sum(miss_a) / len(miss_a), sum(miss_b) / len(miss_b))
        ai, au = sum(inter) / len(inter), sum(union) / len(union)
        return {"intersecting_missed": ai, "union_missed": au, "minimum_missed": mi, "minimum_covered": mi - ai,
                "maximum_covered": au - ai}
    cols = list(T5)
    rows = [["paper (ChatGPT vs Pynguin)"] + [fmt(T5[c]) for c in cols]]
    pairs = [a for a in auth.values() if a["gpt_missed"] is not None and a["pyn_missed"] is not None]
    if pairs:
        s = summary([len(a["gpt_missed"] & a["pyn_missed"]) for a in pairs], [len(a["gpt_missed"] | a["pyn_missed"]) for a in pairs],
                    [len(a["gpt_missed"]) for a in pairs], [len(a["pyn_missed"]) for a in pairs])
        rows.append([f"authors' files (n={len(pairs)})"] + [fmt(s[c]) for c in cols])
        for c in cols:
            rep.add("5", "all", c, "authors' files", "chatgpt vs pynguin", s[c], len(pairs))
    if (RESULTS / "overlap.csv").exists():
        ov = pd.read_csv(RESULTS / "overlap.csv")
        ov = ov[(ov.which == "iter1") & (ov.tool_b == "pynguin")]
        for t, g in ov.groupby("tool_a"):
            pp = g.groupby("program")[["intersecting_missed", "union_missed", "missed_a", "missed_b"]].mean()
            s = summary(*(pp[c].tolist() for c in ("intersecting_missed", "union_missed", "missed_a", "missed_b")))
            rows.append([f"ours {t} vs Pynguin (n={len(pp)})"] + [fmt(s[c]) for c in cols])
            for c in cols:
                rep.add("5", "all", c, "ours", f"{t} vs pynguin", s[c], len(pp))
    rep.md += ["## Table 5: missed statements, ChatGPT/LLM vs Pynguin, p2 (iteration 1)", "",
               "Averages over samples (Pynguin: seeds averaged per sample; LLM: repetition 0). Minimum covered = minimum "
               "missed − intersecting; maximum covered = union − intersecting (the paper's 31.64 is not 50.33 − 17.78 = "
               "32.55: unexplained).", "", md_table(["source"] + cols, rows), ""]


def section_table3(rep, it, llms, label, reference_only, importable=None):
    llm_it = it[it.tool != "pynguin"]
    if llm_it.empty:
        return
    keys = ["tool", "category", "program"] + (["rep"] if "rep" in it else [])
    ch = llm_it.groupby(keys).agg(iter1=("stmt_cov", "first"), iter5_or_last=("stmt_cov", "last"),
                                  best=("stmt_cov", "max"), least=("stmt_cov", "min"),
                                  median_iters=("iteration", "max")).reset_index()
    ch["best_minus_least"] = ch["best"] - ch["least"]
    rows = []
    for cat, vals in T3.items():
        rows.append([cat, "paper ChatGPT (100-300 LOC p1)"] + [fmt(v) for v in vals])
        for t in llms:
            groups = [(label, ch[(ch.tool == t) & (ch.category.map(CAT) == cat)])]
            if importable is not None:  # p1: also the modules that can be imported (decision 15)
                groups.append((f"{label}, importable only", groups[0][1][groups[0][1].program.isin(importable)]))
            for glabel, s in groups:
                if len(s):
                    rows.append([cat, f"ours {t} ({glabel}, n={len(s)})"] + [
                        fmt(s[c].median() if c == "median_iters" else s[c].mean()) for c in T3_COLS])
                    rep.add("3", cat, "iter1", f"ours ({glabel})", t, s["iter1"].mean(), len(s))
    note = ("The paper's Table 3 uses 100-300 LOC p1 (repository README); these chains are on another dataset: "
            "reference only." if reference_only else "Same dataset as the paper (p1).")
    rep.md += [f"## Table 3: iterative improvement{' (reference only)' if reference_only else ''}", "",
               note + " One chain = one program in one repetition.", "",
               md_table(["category", "source", "iter 1", "iter 5 (or last)", "best", "best − least", "median iterations"], rows), ""]


def section_table4(rep, jobs, llms):
    cols = {"all_incorrect": "final_incorrect_assert_pct", "assertion_error": "final_incorrect_pct_assertion_error",
            "try_except": "final_incorrect_pct_try_except", "runtime": "final_incorrect_pct_runtime"}
    rows = []
    for cat, vals in T4.items():
        rows.append([cat, "paper ChatGPT"] + [fmt(v) for v in vals])
        for t in llms:
            sub = jobs[(jobs.tool == t) & (jobs.row == (f"{cat} refactored" if cat == "cat1" else cat))]
            p = sub.groupby("program")[[cols[c] for c in T4_COLS]].mean()
            if len(p):
                rows.append([cat, f"ours {t} (n={len(p)})"] + [fmt(p[cols[c]].mean()) for c in T4_COLS])
                for c in T4_COLS:
                    rep.add("4", cat, c, "ours", t, p[cols[c]].mean(), len(p))
    rep.md += ["## Table 4: incorrect assertions (final suites)", "",
               "Paper: % of incorrect assertions, then the share of each cause among the incorrect ones. "
               "The paper does not say which dataset; Cat 1 = refactored modules only (§3.2.3).", "",
               md_table(["category", "source", "all incorrect", "AssertionError", "try/except", "runtime"], rows), ""]


def section_imports(rep, set_name):
    man = json.loads((PHASE1 / "datasets" / set_name / "manifest.json").read_text())
    bad = {n: e for n, e in man["programs"].items() if any(v != "ok" for v in e["import_check"].values())}
    rep.md += ["## Modules that cannot be imported", "",
               f"{len(man['programs']) - len(bad)} of {len(man['programs'])} modules import in both venvs "
               "(scripts/prepare_datasets.py). The others are still run: a test suite that cannot import its module "
               "gets 0 % coverage, for every tool.", ""]
    if bad:
        def why(e):
            first_error = next(v for v in e["import_check"].values() if v != "ok")
            err = re.sub(r"\(/[^)]*\)", "", first_error).replace("|", "/").strip()
            return e.get("note") or err
        rep.md += [md_table(["program", "category", "reason"], [[n, e["category"], why(e)] for n, e in sorted(bad.items())]), ""]


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="small", choices=("small", "pilot", "p2", "p1"))
    args = ap.parse_args()
    jobs = pd.read_csv(RESULTS / "jobs.csv").copy()  # copy: de-fragmented frame
    jobs["row"] = jobs.apply(row_label, axis=1)
    it = pd.read_csv(RESULTS / "iterations.csv")
    tools = [t for t in ("pynguin", "dsc-6.7b", "cl-7b", "qwen-7b", "dsc-1.3b") if t in set(jobs.tool)]
    tools += sorted(set(jobs.tool) - set(tools))
    llms = [t for t in tools if t != "pynguin"]
    per = jobs.groupby(["tool", "row", "program"], as_index=False)[["stmt_cov", "stmt_branch_cov", "branch_cov"]].mean()
    rep = Report(f"Phase 1 vs Bhatia et al. (2024): {args.set}")
    rep.md += ["Paper values from arXiv 2312.10622v2. Ours: LLM repetitions and Pynguin seeds averaged per program, "
               "then over programs (n = programs). Generated by `scripts/compare_paper.py`.", ""]
    if args.set in ("small", "pilot"):
        section_table1(rep, per, tools, llms)
        section_stored_small(rep, jobs)
        section_table3(rep, it, llms, "0-100 LOC", reference_only=True)
        section_table4(rep, jobs, llms)
    elif args.set == "p2":
        auth = authors_p2()
        section_table2(rep, per, tools, llms, auth)
        section_table5(rep, auth)
        section_table4(rep, jobs, llms)
        section_imports(rep, "p2")
    else:
        man = json.loads((PHASE1 / "datasets" / "p1" / "manifest.json").read_text())
        importable = {n for n, e in man["programs"].items() if all(v == "ok" for v in e["import_check"].values())}
        section_table3(rep, it, llms, "p1", reference_only=False, importable=importable)
        section_table4(rep, jobs, llms)
        section_imports(rep, "p1")
    (RESULTS / "paper_comparison.md").write_text("\n".join(rep.md))
    with open(RESULTS / "paper_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["table", "row", "metric", "source", "tool", "value", "n"])
        w.writeheader()
        w.writerows(rep.long)
    print("written:", RESULTS / "paper_comparison.md", RESULTS / "paper_comparison.csv")


if __name__ == "__main__":
    main()
