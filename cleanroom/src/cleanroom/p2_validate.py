"""Execution validation of p2 programs whose project context was resolved (p2_context).

Per resolved program, in a fresh sandbox copy of its context (network disabled, stdin closed,
isolated interpreter, 3 repetitions, as in execval):
  V1  import the benchmark module from flat/ with pkgroot/ and the release's external site
      directory (if any) on sys.path;
  V3  import every other module of the context (flat names and dotted package names), so
      imports that run only inside functions are also exercised.
Before copying, every context file is checked against the hash recorded in resolution.json;
the external site directory's tree hash is checked before and after.

    python3 -m cleanroom.p2_validate --resolution STAMP
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import execval, integrity, manifest, p2_context, paths
from . import provenance as pv

PROTOCOL = "execval-ctx-1"


def context_modules(files: list[dict]) -> list[str]:
    """Importable module names of a context (excluding the benchmark module)."""
    mods = []
    for f in files:
        p = f["path"]
        if f["kind"] == "benchmark_module":
            continue
        if p.startswith("flat/"):
            mods.append(Path(p).stem)
        elif p.startswith("pkgroot/"):
            rel = p[len("pkgroot/"):-len(".py")].replace("/", ".")
            mods.append(rel[: -len(".__init__")] if rel.endswith(".__init__") else rel)
    return sorted(set(mods))


def verify_context_files(context: dict) -> list[str]:
    root = Path(context["root"])
    bad = []
    for f in context["files"]:
        p = root / f["path"]
        if not p.is_file() or pv.sha256(p.read_bytes()) != f["sha256"]:
            bad.append(f["path"])
    return bad


def site_for(project: str, decision: dict, externals: dict) -> str | None:
    for key, res in externals.get("results", {}).items():
        name, _, version = key.partition("==")
        if name == project and version in decision["release_set"] and res.get("status") == "INSTALLED":
            return res["site"]
    return None


def decide(v1: dict, v3: dict[str, dict], context_problems: list[str], site_changed: bool) -> dict:
    if context_problems:
        return {"execution_verified": False, "outcome": "FAIL_CONTEXT_INTEGRITY",
                "outcome_reason": "context files differ from resolution record: " + ", ".join(context_problems)}
    base = execval.decide({"v1_import": v1})
    if not base["execution_verified"]:
        return base
    failed = {m: r["outcome"] for m, r in v3.items() if r["outcome"] != "IMPORT_OK" or not r["consistent"]}
    if failed:
        return {"execution_verified": False, "outcome": "FAIL_CONTEXT_MODULE_IMPORT",
                "outcome_reason": "context modules failing or inconsistent: "
                                  + ", ".join(f"{m}={o}" for m, o in sorted(failed.items()))}
    if site_changed:
        return {"execution_verified": False, "outcome": "FAIL_SITE_MODIFIED",
                "outcome_reason": "external site directory changed during validation"}
    return {"execution_verified": True, "outcome": "VERIFIED_IMPORT_WITH_CONTEXT",
            "outcome_reason": f"benchmark module and {len(v3)} context modules import consistently "
                              "(network disabled)" + base["outcome_reason"].split("no developer tests", 1)[-1]}


def validate_sample(pid: str, target_name: str, decision: dict, site: str | None, run_dir: Path,
                    sandbox_base: Path, python: Path) -> dict:
    context = decision["context"]
    slug = pid.replace("/", "__")
    out_dir = run_dir / "programs" / slug
    out_dir.mkdir(parents=True)
    problems = verify_context_files(context)
    sb = sandbox_base / slug
    shutil.copytree(context["root"], sb)
    extra = [str(sb / "pkgroot")] + ([site] if site else [])
    site_before = execval.tree_hashes(Path(site)) if site else {}
    v1 = execval.validate_import({}, sb / "flat", python, Path(target_name).stem, tuple(extra))
    v3 = {m: execval.validate_import({}, sb / "flat", python, m, tuple(extra))
          for m in context_modules(context["files"])}
    site_changed = bool(site) and execval.tree_hashes(Path(site)) != site_before
    result = {"program_id": pid, "protocol": PROTOCOL, "release_set": decision["release_set"],
              "artifact_used": decision["artifact_used"], "context_files": context["files"],
              "sys_path_after_cwd": ["<sandbox>/pkgroot"] + ([site] if site else []),
              "context_integrity_problems": problems, "v1_import": v1,
              "v3_context_imports": {m: {k: r[k] for k in ("outcome", "consistent", "first_result",
                                                         "side_effect_files")} for m, r in v3.items()},
              "site_unchanged": not site_changed}
    result.update(decide(v1, v3, problems, site_changed))
    (out_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(sb)
    return result


def run(stamp: str) -> Path:
    python = execval.ENV_PYTHON
    env = execval.environment_record(python)
    if env["version_info"] != [3, 10, 12]:
        raise RuntimeError(f"expected Python 3.10.12, got {env['version']}")
    before = integrity.assert_originals_intact()
    res_dir = p2_context.OUT_DIR / stamp
    resolution = json.loads((res_dir / "resolution.json").read_text(encoding="utf-8"))
    ext_path = res_dir / "externals.json"
    externals = json.loads(ext_path.read_text(encoding="utf-8")) if ext_path.exists() else {}
    rows = {r["program_id"]: r for r in manifest.read_manifest(paths.MANIFEST_CSV)}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = execval.RUNS_DIR / run_id
    run_dir.mkdir(parents=True)
    sandbox_base = execval.SANDBOX_ROOT / run_id
    summary = []
    for project, pres in resolution.items():
        for s, d in pres["samples"].items():
            if d.get("decision") != p2_context.RESOLVED:
                continue
            pid = d["program_id"]
            r = validate_sample(pid, Path(rows[pid]["target"]).name, d, site_for(project, d, externals),
                                run_dir, sandbox_base, python)
            print(f"{pid:12} {project:20} {r['outcome']}", flush=True)
            summary.append({k: r[k] for k in ("program_id", "execution_verified", "outcome", "outcome_reason")})
    after = integrity.assert_originals_intact()
    meta = {"run_id": run_id, "protocol": PROTOCOL, "environment": env, "resolution": stamp,
            "manifest_sha256": pv.sha256(paths.MANIFEST_CSV.read_bytes()),
            "repetitions": execval.REPETITIONS, "import_timeout_s": execval.IMPORT_TIMEOUT_S,
            "network": "disabled (unshare -n)", "integrity_before": before.passed,
            "integrity_after": after.passed,
            "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    with open(run_dir / "results.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(summary)
    if sandbox_base.exists():
        sandbox_base.rmdir()
    execval.seal(run_dir)
    return run_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cleanroom.p2_validate")
    ap.add_argument("--resolution", required=True)
    args = ap.parse_args(argv)
    print(f"run directory: {run(args.resolution).relative_to(paths.CLEANROOM)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
