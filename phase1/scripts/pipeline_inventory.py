"""Stage A of the full-dataset pipeline: the inventory of programs a campaign can use (PIPELINE.md).

Source of truth: datasets/dataset_manifest.json (every program the repository holds, with set, category, path and
sha256, and every program the paper counts but the repository lacks). The inventory checks it against the authors'
files (validate_datasets.check: same files, same bytes, no unlisted program) and against the lists the runner uses
(the 0_100 LOC folders; datasets/<set>/manifest.json), then records for every program which tool runs it in which
experiment and round (config/pipeline.yaml), and why a tool does not.

Read-only: no program is imported, no venv, dataset or result is changed. Called by scripts/pipeline.py.
"""
import csv
import json
from pathlib import Path

import validate_datasets as vd
import yaml
from common import CONFIG_DIR, PHASE1, PYNGUIN_BIN, REPO, RUNNER_PY, now_iso, sha256_text

MANIFEST = PHASE1 / "datasets" / "dataset_manifest.json"
CATS = ("cat1_scripts", "cat2_functions", "cat3_classes")
SMALL_ROOT = REPO / "0_100 LOC"


def load_pipeline_config():
    with open(CONFIG_DIR / "pipeline.yaml") as f:
        return yaml.safe_load(f)


def rounds_available(cfg, tool):
    """Round r = Pynguin seed cfg.pynguin.seeds[r] / LLM repetition r."""
    return range(len(cfg["pynguin"]["seeds"])) if tool == "pynguin" else range(cfg["repetitions"]["llm"])


def config_errors(pcfg, cfg):
    """Problems in config/pipeline.yaml that would make a job's experiment ambiguous or impossible."""
    errs, owner = [], {}
    known_sets = set(cfg["program_sets"])
    for s in pcfg["sets"]:
        if s not in known_sets:
            errs.append(f"pipeline.yaml sets: {s!r} is not a program set of experiment.yaml")
    for exp, e in pcfg["experiments"].items():
        for t in e["tools"]:
            if t != "pynguin" and t not in cfg["llm_tools"]:
                errs.append(f"experiment {exp}: unknown tool {t!r} (experiment.yaml llm_tools)")
                continue
            for r in e["rounds"]:
                if r not in rounds_available(cfg, t):
                    errs.append(f"experiment {exp}: round {r} does not exist for {t} "
                                f"({len(rounds_available(cfg, t))} rounds in experiment.yaml)")
                for s in e["sets"]:
                    key = (s, t, r)
                    if key in owner:
                        errs.append(f"set {s}, tool {t}, round {r} belongs to both {owner[key]} and {exp}")
                    owner[key] = exp
        for s in e["sets"]:
            if s not in pcfg["sets"]:
                errs.append(f"experiment {exp}: set {s!r} not in pipeline.yaml sets")
    return errs


def experiment_of(pcfg, cfg, set_name, tool, rnd):
    """The experiment a job belongs to, or None (not scheduled by config/pipeline.yaml)."""
    if tool == "pynguin" and set_name in (cfg.get("llm_only_sets") or []):
        return None
    for exp, e in pcfg["experiments"].items():
        if set_name in e["sets"] and tool in e["tools"] and rnd in e["rounds"]:
            return exp
    return None


def schedule(pcfg, cfg, set_name):
    """({tool: {experiment: [rounds]}}, {tool: reason}) for one set."""
    sched, why_not = {}, {}
    tools = ["pynguin"] + [t for t in cfg["llm_tools"] if any(t in e["tools"] for e in pcfg["experiments"].values())]
    for t in tools:
        for r in rounds_available(cfg, t):
            exp = experiment_of(pcfg, cfg, set_name, t, r)
            if exp:
                sched.setdefault(t, {}).setdefault(exp, []).append(r)
        if t not in sched:
            why_not[t] = ("not in the paper's protocol for this set (Table 3 is ChatGPT only; experiment.yaml "
                          "llm_only_sets): never scheduled" if t == "pynguin" and set_name in (cfg.get("llm_only_sets") or [])
                          else f"no experiment in config/pipeline.yaml schedules {t} on {set_name}")
    return sched, why_not


def _site_packages_hook(py):
    """True / False: the dataset path hook (prepare_datasets.install_hook) is in this venv; None: venv missing."""
    venv = Path(py).parent.parent
    if not venv.exists():
        return None
    return any(venv.glob("lib/python*/site-packages/phase1_paths.pth"))


def prepared(set_name):
    """Can the runner use this set on this machine? The large samples need their rebuilt projects (make datasets)."""
    if set_name == "small":
        return {"prepared": SMALL_ROOT.exists(), "detail": "0_100 LOC folders" if SMALL_ROOT.exists() else "0_100 LOC missing"}
    d = PHASE1 / "datasets" / set_name
    deps = (d / "deps").exists()
    hook = {"runner_venv": _site_packages_hook(RUNNER_PY), "pynguin_venv": _site_packages_hook(PYNGUIN_BIN.parent / "python")}
    detail = "rebuilt projects and dependencies present" if deps else \
        f"datasets/{set_name}/deps missing: run make datasets (network; approval needed)"
    if deps and not all(hook.values()):
        detail += "; the import-path hook is not in every venv (run.py installs it at first use)"
    return {"prepared": deps and (d / "manifest.json").exists(), "detail": detail, "path_hook": hook}


def _runner_list(set_name):
    """{<category>/<program>: repository path} as the runner sees the set (run.programs, without its side effects)."""
    if set_name == "small":
        return {f"{c}/{d.name}": str((d / "example.py").relative_to(REPO)) for c in CATS
                for d in sorted((SMALL_ROOT / c).iterdir()) if (d / "example.py").exists()}
    man = json.loads((PHASE1 / "datasets" / set_name / "manifest.json").read_text())
    return {f"{e['category']}/{name}": e["source"] for name, e in man["programs"].items()}


def limitations(p):
    out = []
    ic = p.get("import_check") or {}
    for venv in ("runner", "pynguin"):
        if ic.get(venv) not in (None, "ok"):
            out.append(f"plain import fails as uploaded ({venv} venv): {str(ic[venv])[:200]}")
    if p.get("note"):
        out.append(p["note"])
    return out


def build_inventory(pcfg, cfg, sets=None, harness=False):
    """The inventory dict. `errors` non-empty means the campaign must not start."""
    man = json.loads(MANIFEST.read_text())
    errors, notes = vd.check(man)            # sha256 of every program, no unlisted program, counts
    errors = [f"dataset manifest: {e}" for e in errors] + [f"pipeline.yaml: {e}" for e in config_errors(pcfg, cfg)]
    sets = sets or pcfg["sets"]
    by_set = {}
    for s in sets:
        entries = [p for p in man["programs"] if p["set"] == s]
        listed = {f"{p['category']}/{p['id']}": p for p in entries}
        prep = prepared(s)
        runner = _runner_list(s)
        for k in sorted(set(listed) ^ set(runner)):
            where = ("in the dataset manifest but not in the runner list" if k in listed
                     else "in the runner list but not in the dataset manifest")
            errors.append(f"{s}: {k} is {where}")
        for k in sorted(set(listed) & set(runner)):
            if listed[k]["path"] != runner[k]:
                errors.append(f"{s}: {k} path differs: manifest {listed[k]['path']} vs runner {runner[k]}")
        sched, why_not = schedule(pcfg, cfg, s)
        rows = []
        for k, p in sorted(listed.items()):
            f = REPO / p["path"]
            ok = f.exists() and vd.sha(f) == p["sha256"]
            h = PHASE1 / "harness" / s / p["id"] / "conftest.py"
            rows.append({
                "set": s, "id": p["id"], "key": k, "category": p["category"], "path": p["path"], "sha256": p["sha256"],
                "sha256_verified": ok, "lines": p["lines"], "module": p.get("module", "example"),
                "status": "present" if ok else "changed or missing", "runnable_here": prep["prepared"] and ok,
                "scheduled": sched, "not_scheduled": why_not, "limitations": limitations(p),
                "harness": str(h.relative_to(PHASE1)) if h.exists() else None,
                "harness_used": bool(harness and h.exists()),
            })
        cats = {c: sum(r["category"] == c for r in rows) for c in CATS}
        by_set[s] = {"paper": man["sets"][s]["paper"], "repository": man["sets"][s]["repository"],
                     "n_present": sum(r["status"] == "present" for r in rows),
                     "by_category": {c: n for c, n in cats.items() if n}, "preparation": prep,
                     "scheduled": sched, "not_scheduled": why_not, "used_by": man["sets"][s].get("used_by"),
                     "programs": rows}
    lc = man["missing"]["large_cat1"]
    missing = [{"set": "large_cat1", "slot": sl["id"], "category": sl["category"], "status": sl["status"],
                "expected_lines": sl.get("expected_lines"), "runnable_here": False,
                "note": "possibly p1/cat1_s15, which is run in the p1 set; membership in the six is unknown"
                if sl["status"].startswith("possibly") else "not in the repository; not recovered; never replaced"}
               for sl in lc["slots"]]
    inv = {
        "created": now_iso(),
        "source": str(MANIFEST.relative_to(PHASE1)),
        "dataset_manifest_sha256": sha256_text(MANIFEST.read_text()),
        "pipeline_config_sha256": sha256_text((CONFIG_DIR / "pipeline.yaml").read_text()),
        "harness_condition": bool(harness),
        "errors": errors, "notes": notes,
        "sets": by_set,
        "large_cat1": {"paper": lc["expected"], "in_repository": lc["in_repository"], "missing": lc["missing"],
                       "count_assumptions": lc.get("count_assumptions"), "slots": missing},
        "missing_reference_data": man["missing"]["chatgpt_outputs"],
        "discrepancies": man.get("discrepancies", []),
        "totals": {"programs_present": sum(v["n_present"] for v in by_set.values()),
                   "programs_in_manifest": len(man["programs"]),
                   "large_cat1_missing": lc["missing"]},
    }
    inv["inventory_sha256"] = sha256_text(json.dumps({k: inv[k] for k in ("sets", "large_cat1")}, sort_keys=True,
                                                     default=str))
    return inv


def inventory_rows(inv):
    """Flat rows: one per program per set, then one per missing large Cat 1 slot."""
    rows = []
    for s, info in inv["sets"].items():
        for r in info["programs"]:
            rows.append({
                "set": s, "program": r["key"], "category": r["category"], "status": r["status"],
                "sha256": r["sha256"], "sha256_verified": r["sha256_verified"], "lines": r["lines"], "path": r["path"],
                "runnable_here": r["runnable_here"],
                "scheduled": "; ".join(f"{t}: " + ", ".join(f"{e} r{'/'.join(map(str, rs))}" for e, rs in ex.items())
                                       for t, ex in r["scheduled"].items()),
                "not_scheduled": "; ".join(f"{t}: {w}" for t, w in r["not_scheduled"].items()),
                "limitations": " | ".join(r["limitations"]), "harness": r["harness"] or ""})
    for m in inv["large_cat1"]["slots"]:
        rows.append({"set": "large_cat1", "program": m["slot"], "category": m["category"], "status": m["status"],
                     "sha256": "", "sha256_verified": "", "lines": "", "path": "", "runnable_here": False,
                     "scheduled": "", "not_scheduled": "all tools: " + m["note"], "limitations": "", "harness": ""})
    return rows


def write_csv(path, rows):
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, "x", newline="") as f:     # "x": never overwrite
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def summary_lines(inv):
    out = []
    for s, info in inv["sets"].items():
        out.append(f"{s:6} paper {info['paper']['n']:>3}  present {info['n_present']:>3}  "
                   + "  ".join(f"{c} {n}" for c, n in info["by_category"].items())
                   + f"  | prepared here: {'yes' if info['preparation']['prepared'] else 'no'}")
        for t, ex in info["scheduled"].items():
            out.append(f"         {t:9} " + ", ".join(f"{e} rounds {rs}" for e, rs in ex.items()))
        for t, w in info["not_scheduled"].items():
            out.append(f"         {t:9} not scheduled: {w}")
        if not info["preparation"]["prepared"]:
            out.append(f"         {info['preparation']['detail']}")
    lc = inv["large_cat1"]
    out.append(f"large Cat 1: paper {lc['paper']}, at most {len(lc['in_repository'])} in the repository (p1/cat1_s15, "
               f"membership unknown); missing {lc['missing']}: never replaced")
    out.append(f"missing reference data (authors' ChatGPT outputs): {len(inv['missing_reference_data'])} items")
    out.append(f"{inv['totals']['programs_present']} programs present and verified in the sets above "
               f"({inv['totals']['programs_in_manifest']} in the dataset manifest)")
    return out
