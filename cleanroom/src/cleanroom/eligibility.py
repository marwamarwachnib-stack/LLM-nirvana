"""Combine the static manifest, execution-validation runs, the p2 import evidence and the p2
context resolution into benchmark/eligibility.csv (all manifest rows) and a status report.

    python3 -m cleanroom.eligibility --run RUN_ID --evidence STAMP \
        [--resolution STAMP --ctx-run RUN_ID] [--report NAME]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import execval, integrity, manifest, p2_context, p2_evidence, paths

ELIGIBILITY_CSV = paths.BENCHMARK_DIR / "eligibility.csv"
REPORT = paths.REPORTS_DIR / "A4_eligibility_status.md"
REPORT_A5 = paths.REPORTS_DIR / "A5_eligibility_status.md"
FIELDS = ["program_id", "set", "category", "in_scope", "static_status", "attempted",
          "execution_verified", "outcome", "outcome_reason", "run_id",
          "import_consistent", "devtests_as_shipped", "devtests_vs_example", "devtests_skipped",
          "solution_module_evidence", "devtest_oracle", "p2_import_evidence",
          "p2_origin_project", "p2_release_set", "p2_context_decision", "p2_context_reason"]

# User decision (phase A5): the example.py substitution is an evidence-backed reference oracle
# for Cat 2 only (Exercism config.json); for Cat 3 it is an inference, documented separately.
ORACLE = {"cat2_functions": "EVIDENCE_BACKED_REFERENCE (config.json: solution/test/example)",
          "cat3_classes": "INFERRED_ONLY (no config.json; not adopted as reference)"}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_run(run_id: str) -> tuple[dict, dict[str, dict]]:
    run_dir = execval.RUNS_DIR / run_id
    meta = json.loads((run_dir / "run_meta.json").read_text(encoding="utf-8"))
    results = {}
    for f in sorted((run_dir / "programs").glob("*/result.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        results[r["program_id"]] = r
    return meta, results


def load_evidence(stamp: str) -> list[dict]:
    with open(p2_evidence.OUT_DIR / stamp / "evidence.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _frac(v: dict | None) -> str:
    return "" if not v else f"{v.get('passed')}/{v.get('tests')}"


def load_resolution(stamp: str) -> dict[str, dict]:
    """program_id -> {project, release_set, decision, reason} from a p2_context run."""
    data = json.loads((p2_context.OUT_DIR / stamp / "resolution.json").read_text(encoding="utf-8"))
    out = {}
    for project, pres in data.items():
        for s, d in pres["samples"].items():
            out[d["program_id"]] = {"project": project, "release_set": d.get("release_set") or pres["release_set"],
                                    "matching": d.get("matching_releases", []),
                                    "decision": d.get("decision", ""), "reason": d.get("reason", "")}
    return out


def combine(rows: list[dict], run_id: str, results: dict[str, dict], evidence: list[dict],
            resolution: dict[str, dict] | None = None, ctx_run_id: str = "",
            ctx_results: dict[str, dict] | None = None) -> list[dict]:
    ev_by = defaultdict(list)
    for e in evidence:
        ev_by[e["program_id"]].append(f"{e['import']}={e['classification']}")
    resolution, ctx_results = resolution or {}, ctx_results or {}
    out = []
    for r in rows:
        pid = r["program_id"]
        res = results.get(pid)
        rid = run_id
        if res is None and pid in ctx_results:
            res, rid = ctx_results[pid], ctx_run_id
        rz = resolution.get(pid, {})
        row = {"program_id": pid, "set": r["set"], "category": r["category"],
               "in_scope": r["in_scope"], "static_status": r["status"],
               "attempted": res is not None, "p2_import_evidence": ";".join(ev_by.get(pid, [])),
               "devtest_oracle": ORACLE.get(r["category"], "") if r["set"] == "small" else "",
               "p2_origin_project": rz.get("project", ""),
               "p2_release_set": ";".join(rz.get("release_set") or []),
               "p2_context_decision": rz.get("decision", ""), "p2_context_reason": rz.get("reason", "")}
        if res is None:
            reason = ("out of scope (p1, decision 2)" if r["in_scope"] != "True"
                      else f"not executed in this phase: static status {r['status']} ({r['reasons']})")
            row.update(execution_verified=False, outcome="NOT_ATTEMPTED", outcome_reason=reason, run_id="")
        else:
            v2a, v2b = res.get("v2a_as_shipped"), res.get("v2b_reference")
            row.update(execution_verified=res["execution_verified"], outcome=res["outcome"],
                       outcome_reason=res["outcome_reason"], run_id=rid,
                       import_consistent=res["v1_import"]["consistent"],
                       devtests_as_shipped=_frac(v2a), devtests_vs_example=_frac(v2b),
                       devtests_skipped="" if not v2b else v2b.get("skipped"),
                       solution_module_evidence=res.get("solution_module", {}).get("evidence", ""))
        out.append({k: row.get(k, "") for k in FIELDS})
    return out


def render(table: list[dict], meta: dict, results: dict, evidence: list[dict], stamp: str) -> str:
    L: list[str] = []
    w = L.append
    env = meta["environment"]
    w("# A4 — Eligibility status after execution validation\n")
    w("Generated by `python3 -m cleanroom.eligibility` from `benchmark/manifest.csv`, the sealed "
      f"execution-validation run `runs/execval/{meta['run_id']}/` and the p2 evidence "
      f"`runs/p2_evidence/{stamp}/`. No number here is typed by hand.\n")
    w(f"- `benchmark/eligibility.csv` SHA-256: `{_sha(ELIGIBILITY_CSV)}`")
    w(f"- `benchmark/manifest.csv` SHA-256: `{meta['manifest_sha256']}`")
    w(f"- Interpreter: `{env['version'].splitlines()[0]}` ({env['implementation']}, `{env['executable']}`), "
      f"platform `{env['platform']}`")
    w(f"- Packages: {', '.join('`' + p + '`' for p in env['pip_freeze'])}")
    w(f"- Protocol `{meta['protocol']}`: {meta['repetitions']} repetitions, import timeout "
      f"{meta['import_timeout_s']} s, test timeout {meta['test_timeout_s']} s, network {meta['network']}")
    w(f"- Original-snapshot integrity: before run `{meta['integrity_before']}`, after run `{meta['integrity_after']}`\n")

    in_scope = [t for t in table if t["in_scope"] == "True"]
    verified = [t for t in in_scope if t["execution_verified"] is True]
    failed = [t for t in in_scope if t["attempted"] and t["execution_verified"] is not True]
    unverified = [t for t in in_scope if not t["attempted"]]
    w("## Summary (103 in-scope programs)\n")
    w("| | Programs |\n|---|---:|")
    w(f"| **Execution-verified** | **{len(verified)}** |")
    w(f"| Attempted, not verified | {len(failed)} |")
    w(f"| Not attempted (static status requires a decision or missing context) | {len(unverified)} |")
    w(f"| Out of scope (p1), not attempted | {sum(t['in_scope'] != 'True' for t in table)} |\n")
    by = defaultdict(Counter)
    for t in in_scope:
        by[f"{t['set']}/{t['category']}"][t["outcome"]] += 1
    outcomes = sorted({t["outcome"] for t in in_scope})
    w("| Group | " + " | ".join(f"`{o}`" for o in outcomes) + " |")
    w("|---|" + "---:|" * len(outcomes))
    for g, c in sorted(by.items()):
        w(f"| {g} | " + " | ".join(str(c[o]) for o in outcomes) + " |")
    w("")

    w("## A. Verified by execution\n")
    w("`execution_verified = True`: the target imports in a fresh Python 3.10.12 interpreter with "
      "identical outcome, output and (absent) side effects in all repetitions; where Exercism "
      "developer tests exist, they ran against `example.py` with identical per-test outcomes in all "
      "repetitions. Verification does **not** mean the developer tests all pass.\n")
    w("Developer tests: *as shipped* = against the Exercism starter module; *vs example.py* = same "
      "unmodified test file, starter replaced in the sandbox by a byte copy of `example.py`.\n")
    w("| Program | Outcome | Dev tests as shipped (passed/total) | Dev tests vs example.py (passed/total) | Skipped | Starter-module evidence |")
    w("|---|---|---|---|---:|---|")
    for t in verified:
        w(f"| `{t['program_id']}` | `{t['outcome']}` | {t['devtests_as_shipped'] or '—'} | "
          f"{t['devtests_vs_example'] or '—'} | {t['devtests_skipped'] if t['devtests_skipped'] != '' else '—'} | "
          f"{t['solution_module_evidence'] or '—'} |")
    w("")
    if failed:
        w("### Attempted but not verified\n")
        for t in failed:
            w(f"- `{t['program_id']}`: `{t['outcome']}` — {t['outcome_reason']}")
        w("")

    w("## B. Not verified (not executed in this phase)\n")
    w("| Program | Static status | Reason |\n|---|---|---|")
    for t in unverified:
        w(f"| `{t['program_id']}` | `{t['static_status']}` | {t['outcome_reason'].split(': ', 1)[-1]} |")
    w("")

    w("## C. p2 `PENDING_CONTEXT`: evidence per unresolved import (nothing installed)\n")
    w("Classification rules (`cleanroom/p2_evidence.py`): `SIBLING_IN_AUTHORS_RUN` = the module is "
      "listed in the authors' saved coverage report for that sample (it was a source file next to the "
      "module in their run); `SIBLING_BY_RELATIVE_IMPORT` = relative import; "
      "`EXTERNAL_PACKAGE_CANDIDATE` = not listed, and a PyPI project with the import name existed "
      "before the snapshot's earliest commit (**weak**: unrelated projects share generic names such as "
      "`utils`, `config`, `context`, `cookies`); `NO_EVIDENCE` = none of these.\n")
    counts = Counter(e["classification"] for e in evidence)
    w("| Classification | Imports |\n|---|---:|")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        w(f"| `{k}` | {v} |")
    w("")
    per = defaultdict(set)
    for e in evidence:
        per[e["program_id"]].add(e["classification"])
    sib = {p2_evidence.SIBLING_IN_AUTHORS_RUN, p2_evidence.SIBLING_BY_RELATIVE_IMPORT}
    groups = {
        "only sibling modules needed (per saved reports)": sorted(p for p, s in per.items() if s <= sib),
        "also needs external package candidates": sorted(
            p for p, s in per.items() if p2_evidence.EXTERNAL_PACKAGE_CANDIDATE in s
            and p2_evidence.NO_EVIDENCE not in s),
        "at least one import without evidence": sorted(
            p for p, s in per.items() if p2_evidence.NO_EVIDENCE in s),
    }
    for label, progs in groups.items():
        w(f"- **{label}** ({len(progs)}): " + ", ".join(f"`{p}`" for p in progs))
    w("")
    w("| Program | Import | Classification | Same name elsewhere in snapshot | PyPI first upload |")
    w("|---|---|---|---|---|")
    for e in evidence:
        w(f"| `{e['program_id']}` | `{e['import']}` | `{e['classification']}` | "
          f"{e['same_name_elsewhere_in_snapshot'] or '—'} | {e['pypi_first_upload_utc'] or '—'} |")
    w("")
    return "\n".join(L)


def render_a5(table: list[dict], meta: dict, ctx_meta: dict, resolution_stamp: str,
              resolution: dict[str, dict], ctx_results: dict[str, dict]) -> str:
    L: list[str] = []
    w = L.append
    w("# A5 — Eligibility status after p2 context resolution\n")
    w("Generated by `python3 -m cleanroom.eligibility` from `benchmark/manifest.csv`, execution run "
      f"`runs/execval/{meta['run_id']}/` (51 candidates), context resolution "
      f"`runs/p2_context/{resolution_stamp}/` and context execution run "
      f"`runs/execval/{ctx_meta['run_id']}/`. No number here is typed by hand.\n")
    w(f"- `benchmark/eligibility.csv` SHA-256: `{_sha(ELIGIBILITY_CSV)}`")
    w(f"- Context run protocol `{ctx_meta['protocol']}`: {ctx_meta['repetitions']} repetitions, import "
      f"timeout {ctx_meta['import_timeout_s']} s, network {ctx_meta['network']}; integrity before/after "
      f"`{ctx_meta['integrity_before']}`/`{ctx_meta['integrity_after']}`\n")
    ins = [t for t in table if t["in_scope"] == "True"]
    groups = defaultdict(Counter)
    for t in ins:
        state = ("verified" if t["execution_verified"] is True else
                 "attempted, not verified" if t["attempted"] else "not verified")
        groups[f"{t['set']}/{t['category']}"][state] += 1
    states = ["verified", "attempted, not verified", "not verified"]
    w("## Summary (103 in-scope programs)\n")
    w("| Group | " + " | ".join(states) + " |\n|---|" + "---:|" * len(states))
    tot = Counter()
    for g, c in sorted(groups.items()):
        tot.update(c)
        w(f"| {g} | " + " | ".join(str(c[s]) for s in states) + " |")
    w("| **all** | " + " | ".join(f"**{tot[s]}**" for s in states) + " |\n")

    p2 = [t for t in ins if t["set"] == "p2"]
    pend = [t for t in p2 if t["static_status"] == manifest.PENDING_CONTEXT]
    newly = [t for t in pend if t["execution_verified"] is True]
    w("## p2 programs with missing context (31)\n")
    w(f"- Newly execution-verified with a reconstructed context: **{len(newly)}**")
    w(f"- Unresolved: **{sum(t['p2_context_decision'].startswith('UNRESOLVED') for t in pend)}**")
    w(f"- Resolved but failing execution: **{sum(t['p2_context_decision'] == 'RESOLVED' and t['execution_verified'] is not True for t in pend)}**\n")
    w("| Program | Project | Release set | Context decision | Execution | Reason |\n|---|---|---|---|---|---|")
    for t in pend:
        w(f"| `{t['program_id']}` | {t['p2_origin_project']} | {t['p2_release_set'] or '—'} | "
          f"`{t['p2_context_decision']}` | `{t['outcome']}` | {t['p2_context_reason'] or t['outcome_reason']} |")
    w("")
    w("### Context composition (resolved programs)\n")
    w("Kinds: `benchmark_module` = the snapshot module; `benchmark_sibling` = the authors' own flattened "
      "copy of a sibling module, present in the snapshot as another sample and verified against the "
      "same release set; `release_verbatim` = release file, unchanged; `release_derived` = release "
      "file with project-internal imports flattened by derivation F (line numbers kept).\n")
    w("| Program | Release artifact | benchmark_sibling | release_verbatim | release_derived | Context modules imported (V3) |")
    w("|---|---|---:|---:|---:|---:|")
    for t in pend:
        r = ctx_results.get(t["program_id"])
        if not r:
            continue
        k = Counter(f["kind"] for f in r["context_files"])
        w(f"| `{t['program_id']}` | `{r['artifact_used']}` | {k['benchmark_sibling']} | {k['release_verbatim']} | "
          f"{k['release_derived']} | {len(r['v3_context_imports'])} |")
    w("")
    w("## Cross-checks (p2 programs already verified in A4)\n")
    w("Matching releases for the 12 standard-library-only p2 programs (used to intersect release sets):\n")
    w("| Program | Project | Matching releases |\n|---|---|---|")
    for t in p2:
        rz = resolution.get(t["program_id"])
        if t["static_status"] == manifest.CANDIDATE:
            w(f"| `{t['program_id']}` | {rz['project'] if rz else '— (no hypothesis)'} | "
              f"{', '.join(rz['matching']) if rz else '—'} |")
    w("")
    w("## Developer-test oracle (small set)\n")
    for cat, label in ORACLE.items():
        n = sum(t["category"] == cat for t in ins)
        w(f"- `{cat}` ({n} programs): {label}")
    w("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cleanroom.eligibility")
    ap.add_argument("--run", required=True, help="execution-validation run id (51 candidates)")
    ap.add_argument("--evidence", required=True, help="p2 evidence stamp")
    ap.add_argument("--resolution", help="p2_context resolution stamp")
    ap.add_argument("--ctx-run", help="execution run of the resolved contexts")
    args = ap.parse_args(argv)
    integrity.assert_originals_intact()
    rows = manifest.read_manifest(paths.MANIFEST_CSV)
    meta, results = load_run(args.run)
    if meta["manifest_sha256"] != _sha(paths.MANIFEST_CSV):
        raise RuntimeError("run was made against a different manifest")
    evidence = load_evidence(args.evidence)
    resolution, ctx_meta, ctx_results = {}, None, {}
    if args.resolution:
        resolution = load_resolution(args.resolution)
    if args.ctx_run:
        ctx_meta, ctx_results = load_run(args.ctx_run)
        if ctx_meta["manifest_sha256"] != _sha(paths.MANIFEST_CSV) or ctx_meta["resolution"] != args.resolution:
            raise RuntimeError("context run does not belong to this manifest/resolution")
    table = combine(rows, args.run, results, evidence, resolution, args.ctx_run or "", ctx_results)
    with open(ELIGIBILITY_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(table)
    if ctx_meta:
        report = REPORT_A5
        report.write_text(render_a5(table, meta, ctx_meta, args.resolution, resolution, ctx_results),
                          encoding="utf-8")
    else:
        report = REPORT
        report.write_text(render(table, meta, results, evidence, args.evidence), encoding="utf-8")
    integrity.assert_originals_intact()
    print(json.dumps({"eligibility_csv": _sha(ELIGIBILITY_CSV), "report": str(report.name),
                      "report_sha256": _sha(report), "rows": len(table)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
