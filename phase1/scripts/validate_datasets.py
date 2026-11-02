"""Dataset validation (EXPERIMENTAL_WORKFLOW.md, step 1; decision 21).

datasets/dataset_manifest.json lists every program the campaign uses (set, category, path in the authors' repository,
sha256, provenance, the authors' stored artifacts) and every program the paper counts but the repository lacks.
This script checks the authors' files against it: same files, same bytes, same counts, missing still missing. It only
reads the benchmark; --write (re)builds the manifest from the repository and the per-set manifests.

    .venv/bin/python scripts/validate_datasets.py            # check: exit 1 on any difference
    .venv/bin/python scripts/validate_datasets.py --write    # rebuild datasets/dataset_manifest.json
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from common import PHASE1, REPO, atomic_write_json, now_iso
from prepare_datasets import P1_MISSING

MANIFEST = PHASE1 / "datasets" / "dataset_manifest.json"
SMALL = "0_100 LOC"
CATS = ("cat1_scripts", "cat2_functions", "cat3_classes")
PAPER = {"small": {"n": 60, "cat1_scripts": 20, "cat2_functions": 20, "cat3_classes": 20,
                   "evidence": "§2.2: 60 small modules, 20 per category; 0_100 LOC/README"},
         "p2": {"n": 43, "evidence": "§2.2: 49 large = 20 Cat 2 + 23 Cat 3 + 6 Cat 1; the 43 Cat 2/3 ones are p2 "
                                     "(README: Lukasczyk et al. benchmark); Table 2 means need the 41 with ChatGPT reports"},
         "p1": {"n": 40, "cat2_functions": 20, "cat3_classes": 20,
                "evidence": "Table 3 / Fig. 6 (p1 README); n = 20 + 20 inferred from Table 3's values"},
         "large_cat1": {"n": 6, "evidence": "§2.2 ('6 in Category 1'); Table 3 Cat 1 row 56.833 % = 341/6"}}
USED_BY = {"small": ["Table 1"], "p2": ["Table 2", "Fig. 4", "Fig. 5", "Table 5", "Fig. 7"],
           "p1": ["Table 3", "Fig. 6"], "large_cat1": ["Table 3 (Cat 1 row)", "Fig. 6 (Cat 1 line)"]}
CHATGPT_MISSING = [
    {"item": "small set: ChatGPT test suites and coverage reports (60 programs, incl. the refactored Cat 1 modules)",
     "needed_for": ["Table 1 ChatGPT columns", "Table 1 p-values", "Table 1 'Category 1 (refactored)' row"]},
    {"item": "p1: ChatGPT suites and coverage of each improvement iteration (40 modules + the 6 large Cat 1 modules)",
     "needed_for": ["Table 3", "Fig. 6"]},
    {"item": "p2 samples 8 and 10: ChatGPT coverage reports (test files are stored)", "needed_for": ["Table 2 (n = 41, not 43)"]},
    {"item": "p2 samples 1, 2, 7 and 10: ChatGPT compilation reports (39 of 43 are stored)", "needed_for": ["Table 4"]},
    {"item": "assertion classification behind Table 4, and which dataset it uses (of the 39 stored p2 compilation "
             "reports, 10 show tests that ran, 20 only errors, 9 'No test classes found')", "needed_for": ["Table 4"]},
]
EXERCISM = "https://github.com/exercism/python"
# p1 modules for which our rebuild recorded no upstream source (recovery_2026-11-01 report, §1.3)
P1_UNSOURCED = {
    "cat2_s7": "the authors' files name no source (line 1 is an import; cat2/a.txt starts at entry 8)",
    "cat3_s10": "the authors name discord.py examples/converters.py on line 2, which prepare_datasets.p1_samples does "
                "not read (to fix in R0)",
}
# p1 modules whose similarity to every upstream version is 0.0: the comparison could not be made
P1_NOT_COMPARABLE = {
    name: "every upstream version of the file is Python 2 code that does not parse as Python 3, so no similarity "
          "could be computed (verification documented on 2026-11-01; fixed text, not re-checked when the manifest is "
          "regenerated); the authors' file parses as Python 3"
    for name in ("cat2_s2", "cat2_s12")
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path):
    """The file's git blob id (what `git hash-object` prints): comparable with any version in a git history."""
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def small_origin(cat, d):
    if cat == "cat1_scripts":
        return {"kind": "uncertain: source not recorded by the authors",
                "note": "folder names suggest programming-exercise sites (Kattis-style problem names; Advent of Code for "
                        "day2); not verified"}
    return {"kind": "Exercism Python track, reference solution", "repository": EXERCISM,
            "path": f"exercises/practice/{d.name}/.meta/example.py", "git_blob": git_blob(d / "example.py"),
            "evidence": "the file's git blob equals that of a historical version of this path (verification documented "
                        "on 2026-11-01; fixed text, not re-checked when the manifest is regenerated); "
                        "the folder holds the exercise stub and test file" + (", and config.json naming .meta/example.py"
                                                                               if (d / "config.json").exists() else "")}


def entry(set_name, pid, category, rel, origin, artifacts, **extra):
    f = REPO / rel
    return {"set": set_name, "id": pid, "category": category, "path": rel, "sha256": sha(f),
            "lines": len(f.read_text(errors="replace").splitlines()), "status": "present", "origin": origin,
            "authors_artifacts": artifacts, **extra}


def small_programs():
    out = []
    for cat in CATS:
        for d in sorted(p for p in (REPO / SMALL / cat).iterdir() if (p / "example.py").exists()):
            art = sorted(f.name for f in d.iterdir() if f.name in ("test_example.py", "line_coverage.txt",
                                                                     "branch_coverage.txt"))
            out.append(entry("small", d.name, cat, f"{SMALL}/{cat}/{d.name}/example.py", small_origin(cat, d),
                             {"pynguin": art, "chatgpt": []}))
    return out


def large_programs(set_name):
    man = json.loads((PHASE1 / "datasets" / set_name / "manifest.json").read_text())
    out = []
    for name, e in man["programs"].items():
        if set_name == "p2":
            origin = {"kind": "PyPI release (identical apart from import lines)", "dist": e["dist"], "version": e["version"]}
            base = REPO / "100_300 LOC p2"
            art = {t: sorted(f.name for f in (base / folder / name).iterdir() if f.suffix in (".py", ".txt")
                             and f.name != e["source"].split("/")[-1])
                   for t, folder in (("pynguin", "pynguin coverage"), ("chatgpt", "ChatGPT coverage"))
                   if (base / folder / name).is_dir()}
        else:
            o = e.get("origin") or {}
            if o.get("repo"):
                match = ("exact, apart from comments and imports" if o.get("ratio") == 1.0 else
                         f"approximate (most similar version, similarity {o.get('ratio')})" if o.get("ratio") else
                         "not comparable" if o.get("state") else
                         "no version of the file found in the repository")
                origin = {"kind": "GitHub file named by the authors (first lines of the module, or cat*/a.txt)",
                          "match": match, **{k: o.get(k) for k in ("owner", "repo", "branch", "path", "commit", "date",
                                                                   "ratio", "state")},
                          **({"note": P1_NOT_COMPARABLE[name]} if name in P1_NOT_COMPARABLE else {})}
            else:
                origin = {"kind": "uncertain: no upstream source recorded", "note": P1_UNSOURCED.get(name)}
            art = {"pynguin": [], "chatgpt": []}  # p1: modules only
        harness = PHASE1 / "harness" / set_name / name / "conftest.py"
        out.append(entry(set_name, name, e["category"], e["source"], origin, art, module=e["module"],
                         import_check=e.get("import_check"), note=e.get("note"),
                         harness=str(harness.relative_to(PHASE1)) if harness.exists() else None))
    return out


def build():
    commit = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%H", "--", SMALL, "100_300 LOC p1",
                             "100_300 LOC p2"], capture_output=True, text=True).stdout.strip()
    progs = small_programs() + large_programs("p2") + large_programs("p1")
    counts = {}
    for p in progs:
        c = counts.setdefault(p["set"], {"n": 0})
        c["n"] += 1
        c[p["category"]] = c.get(p["category"], 0) + 1
    miss = P1_MISSING["large_cat1"]
    return {
        "created": now_iso(),
        "source": {"repository": "https://github.com/Rey-2001/LLM-nirvana", "upstream_commit": "e330b23581ed26d8b4983bed8766f012f79287ed",
                   "local_commit_of_dataset_folders": commit,
                   "verified": "byte-identical to a fresh clone, 993/993 files (2026-10-31, re-run 2026-11-01)"},
        "rule": "Programs are used exactly as the authors uploaded them; nothing missing is replaced (decision 20, 21).",
        "sets": {s: {"paper": PAPER[s], "repository": counts.get(s, {"n": 0}), "used_by": USED_BY[s]}
                 for s in ("small", "p2", "p1")},
        "programs": progs,
        "missing": {
            "large_cat1": {**{k: miss[k] for k in ("paper", "expected", "in_repository", "missing", "results",
                                                   "replacement")},
                           "expected_role": "Cat 1 module of the large set (paper: procedural script lacking classes "
                                            "and functions, 100-300 LOC); origin uncertain, see possible_origins",
                           "expected_path": "unknown; under H2 likely 100_300 LOC p1/cat1/s<k>/example.py (only s15 "
                                            "uploaded)",
                           "possible_origins": {
                               "H1": "modules of the Lukasczyk et al. benchmark (paper §2.2: the 49 large modules, six "
                                     "of them Cat 1, came from it); the 11 projects behind p2 hold no strict-definition "
                                     "candidate; the benchmark's full list (Zenodo 10.5281/zenodo.6838658) is unread",
                               "H2": "GitHub scripts collected like p1 (s15, the only one uploaded, is one; p1 README; "
                                     "Table 3 uses them)",
                               "status": "uncertain: neither verified"},
                           "count_assumptions": {
                               "A": "Table 3's six = the six of §2.2: 60 + 43 + 40 + 6 = 149 programs needed, 5-6 missing",
                               "B": "different sets: 60 + 43 + 40 + 6 + 6 = 155 needed, 11-12 missing",
                               "status": "A is the simpler reading, not verified"},
                           "slots": [{"id": s, "status": "possibly present: p1/cat1_s15 (membership unknown)" if i == 0
                                      else "missing", "category": "cat1_scripts",
                                      "expected_lines": "stated 100-300 (the authors' files do not consistently meet "
                                                        "their stated ranges)"}
                                     for i, s in enumerate(miss["slots"])],
                           "used_by": USED_BY["large_cat1"],
                           "searched": "recovery_2026-11-01/DATASET_RECOVERY_REPORT_2026-11-01.md"},
            "chatgpt_outputs": CHATGPT_MISSING,
        },
        "discrepancies": [
            "small: paper 20/20/20, repository 21 Cat 1 / 19 Cat 2 / 20 Cat 3; Table 1's ChatGPT means fit 20 Cat 1 "
            "(refactored) and, among 19-21, only 19 Cat 2 (which Cat 1 folder the authors left out is unknown). All 60 "
            "are run and reported per folder.",
            "p2: Table 2 averages 41 samples (caption: 40); §2.2's 20/23 split differs from Table 2's 9/32.",
            "p2: §2.2 speaks of 49 large 'projects', one core module each; the 43 p2 modules come from 11 PyPI projects.",
            "p2: 39 ChatGPT compilation reports are stored, not 43 (none for samples 1, 2, 7, 10).",
            "p1: 41 modules = 20 Cat 2 + 20 Cat 3 + cat1_s15; 11 fail a plain import as uploaded (INDEPENDENT_REAUDIT.md §6); "
            "cat2_s7 names no source.",
            "LOC ranges are not met: 0_100 LOC holds day2 (540 lines); by radon SLOC 24 of 43 p2 and 15 of 41 p1 modules "
            "are under 100 (s15: 88); by total lines 10 p2 and 3 p1 modules fall outside 100-300.",
            "Categories are applied loosely: 3 small Cat 1 programs define functions (Cetvrta, Start_Arrangements, Trik); "
            "3 p1 Cat 2 modules define classes (cat2_s12, cat2_s13, cat2_s15).",
        ],
    }


def check(man):
    errors, notes = [], []
    listed = {p["path"]: p for p in man["programs"]}
    for p in man["programs"]:
        f = REPO / p["path"]
        if not f.exists():
            errors.append(f"missing file: {p['path']}")
        elif sha(f) != p["sha256"]:
            errors.append(f"changed file (sha256 differs): {p['path']}")
    now = {p["path"] for p in small_programs()}
    for s in ("p2", "p1"):
        now |= {e["source"] for e in json.loads((PHASE1 / "datasets" / s / "manifest.json").read_text())["programs"].values()}
    for extra in sorted(now - set(listed)):
        errors.append(f"program not in the manifest (record its provenance first): {extra}")
    cat1 = sorted(str(f.relative_to(REPO)) for f in (REPO / "100_300 LOC p1" / "cat1").glob("*/example.py"))
    if cat1 != ["100_300 LOC p1/cat1/s15/example.py"]:
        notes.append(f"large Cat 1 folder changed: {cat1}. A recovered module needs its provenance recorded "
                     "(DATASET_RECOVERY_REPORT.md) and the complete-dataset protocol (EXPERIMENTAL_WORKFLOW.md §5)")
    for s, info in man["sets"].items():
        got = sum(1 for p in man["programs"] if p["set"] == s)
        if got != info["repository"]["n"]:
            errors.append(f"{s}: {got} programs listed, manifest count says {info['repository']['n']}")
    return errors, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="rebuild datasets/dataset_manifest.json")
    args = ap.parse_args()
    if args.write:
        atomic_write_json(MANIFEST, build())
        print("written:", MANIFEST)
    man = json.loads(MANIFEST.read_text())
    errors, notes = check(man)
    for s, info in man["sets"].items():
        print(f"{s:6} paper {info['paper']['n']:>3}  repository {info['repository']['n']:>3}  "
              + "  ".join(f"{k} {v}" for k, v in info["repository"].items() if k != "n"))
    m = man["missing"]["large_cat1"]
    print(f"large Cat 1: paper {m['expected']}, in the repository at most {len(m['in_repository'])}; missing {m['missing']}")
    print(f"missing ChatGPT outputs: {len(man['missing']['chatgpt_outputs'])} items (see the manifest)")
    for n in notes:
        print("NOTE:", n)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(man['programs'])} programs checked: " + ("all identical to the manifest" if not errors else f"{len(errors)} problem(s)"))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
