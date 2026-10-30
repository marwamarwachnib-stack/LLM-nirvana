"""One row per dataset sample the paper expects or the repository holds -> DATASET_FORENSIC_AUDIT.csv (decision 19).

Inputs: the authors' folders (the local copy, byte-identical to github.com/Rey-2001/LLM-nirvana at e330b23, 993/993
files), datasets/{p1,p2}/manifest.json (import checks), env/verify_environment.md (stored suites re-run),
audit/pyc_forensics.csv and audit/import_probe.csv. Small-set modules get a plain import check here (Python 3.10
runner, stdin closed, 20 s). Classification: OK; B = the original repository or unavailable files; C = environment
or execution differences; D = ambiguity in the paper (A, errors in our code, are listed in BUGS_AND_FIXES.md:
none is at sample level).

    .venv/bin/python audit/forensic_inventory.py
"""
import ast
import csv
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE1 = HERE.parent
sys.path.insert(0, str(PHASE1 / "scripts"))
from common import REPO, RUNNER_PY, run_code  # noqa: E402

SMALL, P1, P2 = REPO / "0_100 LOC", REPO / "100_300 LOC p1", REPO / "100_300 LOC p2"
FIELDS = ["sample_id", "dataset", "paper_category", "expected_by", "expected_identity", "original_repo_path",
          "local_path", "in_original_repo", "in_local_copy", "authors_artifacts", "execution_status",
          "failure_classification", "evidence"]
P2_PROJECT_TESTS = {"sample9", "sample10", "sample11", "sample12"}


def structure(path):
    t = ast.parse(path.read_text())
    funcs = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(t))
    classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(t))
    loc = sum(1 for line in path.read_text().splitlines() if line.strip())
    return f"{loc} non-blank lines, {funcs} functions, {classes} classes"


def pyc_verdicts():
    out = {}
    for r in csv.DictReader(open(HERE / "pyc_forensics.csv")):
        folder = str(Path(r["pyc"]).parent.parent)
        out.setdefault(folder, []).append(f"{Path(r['pyc']).name}: {r['verdict']} (source written {r['source_mtime_utc'][:10]})")
    return out


def verify_differences():
    """(sample, tool) -> causes, from the table of differing reports in env/verify_environment.md."""
    out = {}
    for line in (PHASE1 / "env" / "verify_environment.md").read_text().splitlines():
        c = [x.strip() for x in line.strip("|").split("|")]
        if len(c) == 7 and c[0] in ("small", "p2") and c[1] not in ("program", "---"):
            out.setdefault((c[1], c[2]), set()).add(c[6])
    return out


def plain_import(module_file, module="example"):
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(module_file, Path(tmp) / f"{module}.py")
        try:
            p = run_code([str(RUNNER_PY), "-c", f"import {module}"], None, cwd=tmp, capture_output=True, text=True,
                         timeout=20, stdin=__import__("subprocess").DEVNULL)
        except __import__("subprocess").TimeoutExpired:
            return "import did not finish in 20 s"
        return "imports" if p.returncode == 0 else (p.stderr.strip().splitlines() or ["?"])[-1][:120]


def small_rows(pycs, diffs):
    rows = []
    for cat, paper_cat in (("cat1_scripts", "Cat 1"), ("cat2_functions", "Cat 2"), ("cat3_classes", "Cat 3")):
        for d in sorted(p for p in (SMALL / cat).iterdir() if p.is_dir() and p.name != "__pycache__"):
            ex = d / "example.py"
            arts = [n for n in ("test_example.py", "line_coverage.txt", "branch_coverage.txt", "pynguin-report/statistics.csv")
                    if (d / n).exists()]
            status = plain_import(ex)
            if status.startswith("EOFError"):
                status = "script: stops at input() when imported (EOFError), as expected for Cat 1"
            ev = [structure(ex)] + pycs.get(str(d.relative_to(REPO)), [])
            dif = diffs.get((f"{cat}/{d.name}", "pynguin"))
            if cat != "cat1_scripts":
                ev.append("stored Pynguin reports re-run: " + ("identical" if not dif and "line_coverage.txt" in arts else
                                                              "; ".join(dif) if dif else "no statement report stored"))
            rows.append({"sample_id": f"small/{cat}/{d.name}", "dataset": "0_100 LOC", "paper_category": paper_cat,
                         "expected_by": "§2.2 (60 small, 20 per category); Table 1, Table 4 (Cat 1 refactored)",
                         "expected_identity": d.name, "original_repo_path": str(ex.relative_to(REPO)),
                         "local_path": str(ex.relative_to(REPO)), "in_original_repo": True, "in_local_copy": True,
                         "authors_artifacts": "; ".join(arts) or "module only (Pynguin produced no tests for Cat 1, §3.1)",
                         "execution_status": status, "failure_classification": "OK",
                         "evidence": " | ".join(ev)})
    rows.append({"sample_id": "small/cat2_functions/<20th>", "dataset": "0_100 LOC", "paper_category": "Cat 2",
                 "expected_by": "§2.2 and the folder's README: 20 per category", "expected_identity": "unknown",
                 "original_repo_path": "", "local_path": "", "in_original_repo": False, "in_local_copy": False,
                 "authors_artifacts": "", "execution_status": "n/a", "failure_classification": "D",
                 "evidence": "the repository has 21 Cat 1, 19 Cat 2 and 20 Cat 3 folders (all commits checked); Table 1's ChatGPT "
                             "Cat 2 means fit 19 programs (93.26 = 1772/19) and its Cat 1 means 20 programs (97.45 = 1949/20): "
                             "the paper's own numbers use 19 Cat 2 programs, one Cat 1 folder is unused, which one is unknown"})
    return rows


def p2_rows(pycs, diffs):
    man = json.loads((PHASE1 / "datasets" / "p2" / "manifest.json").read_text())["programs"]
    rows = []
    for name, e in sorted(man.items(), key=lambda x: int(x[0][6:])):
        gdir = P2 / "ChatGPT coverage" / name
        rep = (gdir / "compilation_report.txt").read_text(errors="replace") if (gdir / "compilation_report.txt").exists() else ""
        last = (re.findall(r"=+ ([^=]*?) in [\d.]+s =+", rep) or [""])[-1]
        comp = ("no compilation_report.txt" if not rep else "tests never ran (collection error)" if re.fullmatch(r"\d+ errors?", last)
                else f"tests ran: {last}" if last else "no result line")
        arts = ["Pynguin folder: " + ("the project's own tests, not Pynguin's" if name in P2_PROJECT_TESTS else "Pynguin test + reports"),
                "ChatGPT folder: test_example.py" + (" + coverage reports" if (gdir / "statement_coverage.txt").exists()
                                                    else ", no coverage report") + f"; compilation report: {comp}"]
        dif = sorted({c for tool in ("pynguin", "chatgpt") for c in diffs.get((name, tool), set())})
        ev = [f"{e['dist']}=={e['version']} ({e['module']}.py identical to the release apart from import lines)",
              "stored reports re-run: " + ("; ".join(dif) if dif else "identical where stored")] + pycs.get(str(gdir.relative_to(REPO)), [])
        ok = all(v == "ok" for v in e["import_check"].values())
        rows.append({"sample_id": f"p2/{name}", "dataset": "100_300 LOC p2", "paper_category": e["category"].split("_")[0].replace("cat", "Cat "),
                     "expected_by": "§2.2 (large, Lukasczyk et al. benchmark); Table 2, Fig. 4, Fig. 5, Table 5, Fig. 7",
                     "expected_identity": f"{e['module']}.py ({e['dist']})", "original_repo_path": e["source"],
                     "local_path": e["source"], "in_original_repo": True, "in_local_copy": True, "authors_artifacts": " | ".join(arts),
                     "execution_status": "imports in both venvs" if ok else str(e["import_check"]),
                     "failure_classification": "OK" if ok and not dif else "B" if dif else "C", "evidence": " | ".join(ev)})
    return rows


P1_FAILURE = {  # root cause of each plain-import failure (traceback in INDEPENDENT_REAUDIT.md)
    "cat1_s15": ("B", "argparse.parse_args() at import requires --source_path (script)"),
    "cat2_s10": ("B", "the module is Python 3, but imports vbench.benchmark, Python 2 code (exec statement)"),
    "cat2_s11": ("B", "imports win32api: Windows only (the authors' p2 machine was macOS)"),
    "cat2_s2": ("B", "Python 2: str.decode('hex') at import (pacemaker/ssltest.py)"),
    "cat2_s6": ("B", "gaussian_renderer imports diff_gaussian_rasterization: a CUDA extension, NVIDIA GPU only"),
    "cat3_s10": ("B+C", "bot.run('token') at import: login with a literal placeholder token; here DNS fails first (sandbox), "
                        "with network the login fails (invalid token): same outcome"),
    "cat3_s11": ("B+C", "asyncio.run(main()) at import starts the bot with the literal token 'token'; DNS fails here, login fails online"),
    "cat3_s12": ("B", "from .experiment import Experiment: top-level relative import (needs its prompttools package)"),
    "cat3_s14": ("B", "import cPickle: Python 2 (vbench/runner.py)"),
    "cat3_s8": ("B", "from .image_utils import ...: top-level relative import; no source repository version matched"),
    "cat3_s9": ("C", "not invalid: a real-time market simulation runs at import, time.sleep(1) per 1/60 simulated minute "
                     "from 570 to 1000 minutes = 25,800 s (7.2 h); our 120 s import check and 300 s per-file test timeout stop it"),
}


def p1_rows():
    man = json.loads((PHASE1 / "datasets" / "p1" / "manifest.json").read_text())["programs"]
    probe = {r["program"]: r for r in csv.DictReader(open(HERE / "import_probe.csv"))}
    rows = []
    for name, e in sorted(man.items()):
        ok = all(v == "ok" for v in e["import_check"].values())
        o = e.get("origin") or {}
        src = (f"github.com/{o['owner']}/{o['repo']}/{o['path']}" + (f" @ {o['commit'][:12]}" if o.get("commit") else "")
               if o else "not identified")
        ev = [structure(REPO / e["source"]), f"source: {src} ({o.get('state') or 'no repository version matched'})"]
        cls, cause = ("OK", "") if ok else P1_FAILURE[name]
        if not ok:
            pr = probe[name]
            ev.append(f"{cause}; plain import covers {pr['plain_import_stmt_cov']} % of {pr['statements']} statements, "
                      f"a test-style preparation ({pr['preparation']}) {pr['prepared_stmt_cov']} %"
                      + (" and the module then imports" if pr["imported_prepared"] == "True" else ""))
        rows.append({"sample_id": f"p1/{name}", "dataset": "100_300 LOC p1", "paper_category": e["category"].split("_")[0].replace("cat", "Cat "),
                     "expected_by": "Table 3 / Fig. 6 (p1 README: iterative improvement with ChatGPT; not in the 109 of §2.2)",
                     "expected_identity": f"{name} ({o.get('repo', '?')})", "original_repo_path": e["source"], "local_path": e["source"],
                     "in_original_repo": True, "in_local_copy": True,
                     "authors_artifacts": "module only (no tests, reports or .pyc stored for p1)",
                     "execution_status": "imports in both venvs" if ok else "plain import fails: " + next(v for v in e["import_check"].values() if v != "ok")[:100],
                     "failure_classification": cls, "evidence": " | ".join(ev)})
    for i in range(1, 7):
        rows.append({"sample_id": f"large_cat1/#{i}", "dataset": "100-300 LOC Cat 1 (Table 3)", "paper_category": "Cat 1",
                     "expected_by": "§2.2 ('6 in Category 1'); Table 3 Cat 1 row = 341/6 (one module cannot give 56.833)",
                     "expected_identity": "unknown" if i > 1 else "possibly p1/cat1_s15",
                     "original_repo_path": "" if i > 1 else "100_300 LOC p1/cat1/s15/example.py",
                     "local_path": "" if i > 1 else "100_300 LOC p1/cat1/s15/example.py",
                     "in_original_repo": i == 1, "in_local_copy": i == 1, "authors_artifacts": "",
                     "execution_status": "n/a" if i > 1 else "see p1/cat1_s15",
                     "failure_classification": "B" if i > 1 else "D",
                     "evidence": "not in the repository: the only procedural module of 100-300 lines among its 200 module files "
                                 "is p1/cat1/s15; every file content of all 38 commits is in the last commit; no branch, tag, PR, "
                                 "release or second visible fork; p1 numbers its Cat 1 module s15 (others not uploaded)"
                                 if i > 1 else "p1's only Cat 1 module; whether it is one of the six is unknown"})
    return rows


def main():
    pycs, diffs = pyc_verdicts(), verify_differences()
    rows = small_rows(pycs, diffs) + p2_rows(pycs, diffs) + p1_rows()
    out = PHASE1 / "DATASET_FORENSIC_AUDIT.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[(r["dataset"], r["failure_classification"])] = counts.get((r["dataset"], r["failure_classification"]), 0) + 1
    print(len(rows), "rows ->", out)
    for k, v in sorted(counts.items()):
        print(f"  {k[0]:28} {k[1]:4} {v}")


if __name__ == "__main__":
    main()
