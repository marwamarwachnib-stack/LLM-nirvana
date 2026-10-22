"""Hash-pinned installation of the external requirements of resolved p2 releases.

Policy (config/p2_externals.json):
  * candidates are the release's *declared* requirements (from its own metadata), evaluated for
    CPython 3.10 / Linux; a requirement is installed only if one of its import names occurs in
    the import closure of a resolved sample of that release (p2_context resolution.json);
  * version = what pip resolves for the declared specifier, constrained iteratively so that every
    package (including transitive ones) is the newest release uploaded before the cutoff;
  * wheels only; an exactly pinned requirement that exists only as an sdist is built into a wheel
    with the network disabled (`unshare -n`, `pip wheel --no-deps --no-build-isolation --no-index`);
  * installed with `pip install --target <site> --no-deps --require-hashes` into
    /opt/cleanroom/context/site/<release>/ (never into the experiment environment).

    python3 -m cleanroom.p2_externals --resolution RUN_STAMP
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import execval, integrity, p2_context, paths
from . import provenance as pv

CONFIG = paths.CLEANROOM / "config" / "p2_externals.json"
LOCK_DIR = paths.CLEANROOM / "config" / "p2_locks"
SITE_DIR = p2_context.CR_ROOT / "context" / "site"
WORK_DIR = p2_context.CR_ROOT / "context" / "work"
PY = execval.ENV_PYTHON


def pypi_json(name: str, version: str | None = None) -> dict:
    url = f"https://pypi.org/pypi/{name}/json" if version is None else f"https://pypi.org/pypi/{name}/{version}/json"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def newest_before(index: dict, cutoff: str) -> str | None:
    """Newest non-prerelease, non-yanked version whose first upload precedes `cutoff`."""
    probe = ("import json,sys\nfrom packaging.version import Version\n"
             "c=json.load(sys.stdin)\nprint(max(c, key=Version) if c else '')")
    cands = [v for v, files in index["releases"].items()
             if files and not all(f.get("yanked") for f in files)
             and min(f["upload_time_iso_8601"][:19] for f in files) < cutoff]
    out = subprocess.run([str(PY), "-I", "-c", probe + "\n"], input=json.dumps(
        [v for v in cands if not any(t in v for t in ("a", "b", "rc", "dev"))]),
        capture_output=True, text=True, check=True).stdout.strip()
    return out or None


def first_upload(name: str, version: str) -> str:
    files = pypi_json(name, version)["urls"]
    return min(f["upload_time_iso_8601"][:19] for f in files) if files else ""


def applicable(declared: list[str]) -> list[str]:
    """Declared requirements whose environment markers hold for the experiment interpreter."""
    probe = ("import json,sys\nfrom packaging.requirements import Requirement\n"
             "rs=json.load(sys.stdin)\n"
             "print(json.dumps([r for r in rs if Requirement(r).marker is None "
             "or Requirement(r).marker.evaluate()]))")
    return json.loads(subprocess.run([str(PY), "-I", "-c", probe], input=json.dumps(declared),
                                     capture_output=True, text=True, check=True).stdout)


def req_name(req: str) -> str:
    probe = "import sys\nfrom packaging.requirements import Requirement\nprint(Requirement(sys.argv[1]).name)"
    return subprocess.run([str(PY), "-I", "-c", probe, req], capture_output=True, text=True,
                          check=True).stdout.strip()


def build_sdist_only(name: str, version: str, wheels: Path, log: list) -> None:
    """Download the verified sdist and build a wheel with the network disabled."""
    files = pypi_json(name, version)["urls"]
    if any(f["packagetype"] == "bdist_wheel" for f in files):
        return
    sdist = next(f for f in files if f["packagetype"] == "sdist")
    dl = WORK_DIR / "sdists" / sdist["filename"]
    dl.parent.mkdir(parents=True, exist_ok=True)
    if not dl.exists():
        with urllib.request.urlopen(sdist["url"], timeout=120) as r:
            dl.write_bytes(r.read())
    p2_context.verify_artifact(dl, sdist["digests"]["sha256"])
    wheels.mkdir(parents=True, exist_ok=True)
    cmd = ["unshare", "-n", "--", str(PY), "-I", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
           "--no-index", "--no-cache-dir", "-w", str(wheels), str(dl)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    log.append({"step": "build_sdist_offline", "sdist": sdist["filename"], "sdist_sha256": sdist["digests"]["sha256"],
                "returncode": r.returncode, "stdout_tail": r.stdout[-1500:], "stderr_tail": r.stderr[-1500:]})
    if r.returncode != 0:
        raise RuntimeError(f"offline wheel build failed for {name}=={version}")


def resolve_lock(reqs: list[str], cutoff: str, work: Path, log: list) -> list[dict]:
    wheels = work / "local_wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    constraints: dict[str, str] = {}
    for it in range(12):
        (work / "constraints.txt").write_text("".join(f"{c}\n" for c in constraints.values()))
        report = work / f"report_{it}.json"
        cmd = [str(PY), "-I", "-m", "pip", "install", "--dry-run", "--ignore-installed", "--no-cache-dir",
               "--only-binary=:all:", "--find-links", str(wheels), "-c", str(work / "constraints.txt"),
               "--report", str(report), *reqs]
        r = subprocess.run(cmd, capture_output=True, text=True)
        log.append({"step": f"resolve_{it}", "constraints": sorted(constraints.values()),
                    "returncode": r.returncode, "stderr_tail": r.stderr[-1500:]})
        if r.returncode != 0:
            raise RuntimeError(f"resolution failed: {r.stderr[-800:]}")
        items = json.loads(report.read_text())["install"]
        late = []
        for it_ in items:
            meta = it_["metadata"]
            name, version = meta["name"], meta["version"]
            url = it_["download_info"]["url"]
            uploaded = first_upload(name, version)
            it_["_uploaded"] = uploaded
            if uploaded >= cutoff:
                newest = newest_before(pypi_json(name), cutoff)
                if newest is None:
                    raise RuntimeError(f"no pre-cutoff release of {name}")
                late.append(name)
                constraints[name.lower()] = f"{name}=={newest}"
        if not late:
            return [{"name": i["metadata"]["name"], "version": i["metadata"]["version"],
                     "url": i["download_info"]["url"],
                     "sha256": i["download_info"]["archive_info"]["hashes"]["sha256"],
                     "first_upload_utc": i["_uploaded"],
                     "requested": i.get("requested", False)} for i in items]
    raise RuntimeError("constraint iteration did not converge")


def top_level_names(site: Path) -> set[str]:
    return {p.stem if p.suffix == ".py" else p.name for p in site.iterdir()
            if not p.name.endswith((".dist-info", ".data")) and p.name != "bin"}


def install(key: str, spec: dict, needed_imports: set[str], cutoff: str, log: list) -> dict:
    name, _, version = key.partition("==")
    declared = applicable(spec["declared"])
    by_name = {req_name(r): r for r in declared}
    wanted = sorted({spec["import_names"][i] for i in needed_imports if i in spec["import_names"]})
    reqs = [by_name[w] for w in wanted if w in by_name]
    skipped = sorted(set(spec["import_names"].values()) - set(wanted))
    out = {"release": key, "declared_applicable": declared, "needed_import_names": sorted(needed_imports),
           "requirements_installed": reqs, "declared_not_needed": skipped}
    if not reqs:
        out["status"] = "NOTHING_TO_INSTALL"
        return out
    work = WORK_DIR / key
    work.mkdir(parents=True, exist_ok=True)
    for r in reqs:
        n = req_name(r)
        if "==" in r:
            build_sdist_only(n, r.split("==", 1)[1].split(",")[0].strip(), work / "local_wheels", log)
    lock = resolve_lock(reqs, cutoff, work, log)
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = LOCK_DIR / f"{key.replace('==', '-')}.txt"
    lock_file.write_text(f"# {key}: resolved {datetime.now(timezone.utc).date()} with cutoff {cutoff}\n"
                         + "".join(f"{i['name']}=={i['version']} --hash=sha256:{i['sha256']}\n" for i in lock))
    site = SITE_DIR / key
    if site.exists():
        import shutil
        shutil.rmtree(site)
    cmd = [str(PY), "-I", "-m", "pip", "install", "--target", str(site), "--no-deps", "--require-hashes",
           "--no-cache-dir", "--only-binary=:all:", "--find-links", str(work / "local_wheels"),
           "-r", str(lock_file)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    log.append({"step": "install", "returncode": r.returncode, "stderr_tail": r.stderr[-1500:]})
    if r.returncode != 0:
        raise RuntimeError(f"install failed for {key}")
    present = top_level_names(site)
    missing = sorted(i for i in needed_imports if i in spec["import_names"]
                     and spec["import_names"][i] in wanted and i not in present)
    out.update(status="INSTALLED" if not missing else "IMPORT_NAMES_MISSING", lock=lock,
               lock_file=str(lock_file.relative_to(paths.CLEANROOM)), site=str(site),
               site_tree_sha256=pv.sha256(json.dumps(sorted(execval.tree_hashes(site).items())).encode()),
               import_names_missing=missing)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cleanroom.p2_externals")
    ap.add_argument("--resolution", required=True, help="p2_context run stamp")
    args = ap.parse_args(argv)
    integrity.assert_originals_intact()
    run = p2_context.OUT_DIR / args.resolution
    resolution = json.loads((run / "resolution.json").read_text(encoding="utf-8"))
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cutoff = cfg["cutoff_utc"]
    results, log = {}, []
    for key, spec in cfg.items():
        if key.startswith("_") or key == "cutoff_utc":
            continue
        project, _, version = key.partition("==")
        samples = resolution[project]["samples"]
        needed: set[str] = set()
        for s in spec["samples"]:
            d = samples[s]
            if d.get("decision") != p2_context.RESOLVED:
                continue
            if version not in d["release_set"]:
                raise RuntimeError(f"{key} is not in the release set of {s}: {d['release_set']}")
            needed |= set(d["externals"])
        results[key] = install(key, spec, needed, cutoff, log)
    (run / "externals.json").write_text(json.dumps({"results": results, "log": log}, indent=1), encoding="utf-8")
    integrity.assert_originals_intact()
    for k, v in results.items():
        print(f"{k:28} {v['status']:20} installed={v['requirements_installed']} not_needed={v['declared_not_needed']}")
        for i in v.get("lock", []):
            print(f"    {i['name']}=={i['version']}  uploaded {i['first_upload_utc']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
