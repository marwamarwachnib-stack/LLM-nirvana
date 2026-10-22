"""Resolve the missing project context of p2 programs from verified PyPI releases.

Decision procedure (all rules fixed before results are inspected; see reports/A5):
  1. Hypothesis: origin project per sample from the authors' saved reports (config/p2_projects.json).
  2. Release identity: a release *matches* a sample if its artifact contains the module and the
     benchmark copy equals it under normalization N (`provenance.py`). The project's release set
     is the intersection of matching releases over all its samples in the snapshot.
     - empty intersection                        -> UNRESOLVED_NO_COMMON_RELEASE
     - VCS snapshot named in the authors' paths  -> UNRESOLVED_VCS_SNAPSHOT
     - >1 release and required files differ      -> UNRESOLVED_AMBIGUOUS_RELEASE
     - all artifacts (sdist/wheel) of the release set must agree on every required file.
  3. Context = only files required by the sample (transitive import closure):
       pkgroot/<package>/...  release files, verbatim (hash = release member hash), for imports
                              through the package name or relative imports inside it;
       flat/                  the benchmark module (verbatim) and every module it imports *flat*.
                              A flat sibling is (a) the authors' own flattened copy when the
                              snapshot contains it as another sample of the same project that
                              matches the release set, otherwise (b) the release file rewritten
                              by derivation F (`provenance.flatten_imports`: relative and
                              package-absolute imports made flat, as in all flattened samples).
  4. External (non-stdlib, non-project) imports are listed with their importing file and whether
     they run at import time; they are installed separately, hash-pinned (`p2_externals`).

    python3 -m cleanroom.p2_context resolve
"""
from __future__ import annotations

import ast
import json
import shutil
import sys
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import integrity, manifest, paths
from . import provenance as pv
from .stdlib310 import STDLIB_310

PROJECTS_JSON = paths.CLEANROOM / "config" / "p2_projects.json"
CR_ROOT = Path("/opt/cleanroom")
DIST_DIR = CR_ROOT / "context" / "dist"
CONTEXTS_DIR = CR_ROOT / "context" / "contexts"
OUT_DIR = paths.CLEANROOM / "runs" / "p2_context"
CUTOFF_UTC = "2024-01-26T16:51:11"  # earliest commit of the snapshot

RESOLVED = "RESOLVED"
UNRESOLVED_NO_MATCH = "UNRESOLVED_NO_MATCHING_RELEASE"
UNRESOLVED_NO_COMMON = "UNRESOLVED_NO_COMMON_RELEASE"
UNRESOLVED_VCS = "UNRESOLVED_VCS_SNAPSHOT"
UNRESOLVED_AMBIGUOUS = "UNRESOLVED_AMBIGUOUS_RELEASE"
UNRESOLVED_CLOSURE = "UNRESOLVED_IMPORT_CLOSURE"


def load_projects(path: Path = PROJECTS_JSON) -> dict[str, dict]:
    return {k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items() if not k.startswith("_")}


# ---------------------------------------------------------------- PyPI index and artifacts

def release_artifacts(index: dict, cutoff: str = CUTOFF_UTC) -> list[dict]:
    """sdist and wheel files of releases uploaded before `cutoff`, from a PyPI JSON index."""
    out = []
    for version, files in index.get("releases", {}).items():
        for f in files:
            if f.get("packagetype") in ("sdist", "bdist_wheel") and \
                    f["upload_time_iso_8601"][:19] < cutoff and not f.get("yanked"):
                out.append({"version": version, "filename": f["filename"], "url": f["url"],
                            "sha256": f["digests"]["sha256"], "packagetype": f["packagetype"],
                            "upload_time": f["upload_time_iso_8601"][:19]})
    return sorted(out, key=lambda a: (a["upload_time"], a["filename"]))


def verify_artifact(path: Path, expected_sha256: str) -> None:
    got = pv.sha256(path.read_bytes())
    if got != expected_sha256:
        raise RuntimeError(f"hash mismatch for {path.name}: {got} != {expected_sha256}")


def fetch(project: str, out_dir: Path) -> list[dict]:
    """Download (if absent) and verify every pre-cutoff artifact; saves the index used."""
    import urllib.request
    with urllib.request.urlopen(f"https://pypi.org/pypi/{project}/json", timeout=60) as r:
        index = json.load(r)
    (out_dir / "pypi").mkdir(parents=True, exist_ok=True)
    (out_dir / "pypi" / f"{project}.json").write_text(json.dumps(index, indent=1, sort_keys=True),
                                                      encoding="utf-8")
    arts = release_artifacts(index)
    dest = DIST_DIR / project
    dest.mkdir(parents=True, exist_ok=True)
    for a in arts:
        p = dest / a["filename"]
        if not p.exists():
            with urllib.request.urlopen(a["url"], timeout=120) as r:
                data = r.read()
            if pv.sha256(data) != a["sha256"]:
                raise RuntimeError(f"hash mismatch while downloading {a['filename']}")
            p.write_bytes(data)
        verify_artifact(p, a["sha256"])
    return arts


# ---------------------------------------------------------------- release identity

def sample_matches(target: bytes, target_name: str, artifacts: dict[str, dict[str, bytes]],
                   versions: dict[str, str], package: str, renames: dict) -> dict[str, list[dict]]:
    """version -> matching members (artifact, member path, comparison) for one sample."""
    out: dict[str, list[dict]] = {}
    for art, files in artifacts.items():
        for member, data in files.items():
            if member.rsplit("/", 1)[-1] != target_name:
                continue
            try:
                c = pv.compare(target, data, package, renames)
            except (SyntaxError, UnicodeDecodeError):
                continue
            if c.canonical_equal:
                out.setdefault(versions[art], []).append(
                    {"artifact": art, "member": member, **asdict(c)})
    return out


# ---------------------------------------------------------------- import closure

@dataclass
class Closure:
    pkg_files: set[str] = field(default_factory=set)      # paths 'pkg/...py' copied verbatim
    flat_modules: dict[str, str] = field(default_factory=dict)  # flat name -> 'pkg/...py' source
    externals: dict[str, list[dict]] = field(default_factory=dict)  # top name -> importers
    optional_unresolved: list[str] = field(default_factory=list)  # guarded by except ImportError
    problems: list[str] = field(default_factory=list)


def _catches_import_error(h: ast.ExceptHandler) -> bool:
    if h.type is None:
        return True
    types = h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]
    return any(isinstance(t, ast.Name) and t.id in {"ImportError", "ModuleNotFoundError",
                                                     "Exception", "BaseException"} for t in types)


# Names whose appearance in an `if` test makes the guarded imports environment-conditional
# (Python version or platform), e.g. `if hexversion >= ...`, `if platform.system() == 'Windows'`.
VERSION_NAMES = {"version_info", "hexversion", "PY2", "PY3", "PY37", "PY38", "platform", "system"}


def _is_version_test(test: ast.expr) -> bool:
    return any((isinstance(n, ast.Name) and n.id in VERSION_NAMES)
               or (isinstance(n, ast.Attribute) and n.attr in VERSION_NAMES) for n in ast.walk(test))


def parse(data: bytes) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(data.decode("utf-8"))


def _imports(data: bytes) -> list[tuple[ast.stmt, bool, bool]]:
    """(import node, at_import_time, optional) for every import statement outside
    `if TYPE_CHECKING:`. optional = (a) inside a `try` whose handlers catch ImportError, or in
    such a handler (a fallback); or (b) inside a branch of an `if` whose test refers to the
    Python version or the platform (`sys.version_info`, `hexversion`, `sys.platform`,
    `platform.system()`). Optional imports are recorded,
    not required; execution decides whether they run on Python 3.10."""
    tree = parse(data)
    nested: set[int] = set()
    for f in ast.walk(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            nested |= {id(n) for n in ast.walk(f) if n is not f}
    tc: set[int] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.If) and ((isinstance(n.test, ast.Name) and n.test.id == "TYPE_CHECKING")
                                      or (isinstance(n.test, ast.Attribute) and n.test.attr == "TYPE_CHECKING")):
            tc |= {id(m) for b in n.body for m in ast.walk(b)}
    optional: set[int] = set()
    for t in ast.walk(tree):
        if isinstance(t, ast.Try) and any(_catches_import_error(h) for h in t.handlers):
            for part in t.body + [x for h in t.handlers for x in h.body]:
                optional |= {id(m) for m in ast.walk(part)}
        if isinstance(t, ast.If) and _is_version_test(t.test):
            for part in t.body + t.orelse:
                optional |= {id(m) for m in ast.walk(part)}
    return [(n, id(n) not in nested, id(n) in optional) for n in ast.walk(tree)
            if isinstance(n, (ast.Import, ast.ImportFrom)) and id(n) not in tc]


def _module_file(pkg_files: dict[str, bytes], dotted: str) -> str | None:
    base = dotted.replace(".", "/")
    for cand in (f"{base}.py", f"{base}/__init__.py"):
        if cand in pkg_files:
            return cand
    return None


def _parents(path: str) -> list[str]:
    parts = path.split("/")[:-1]
    return [("/".join(parts[:i]) + "/__init__.py") for i in range(1, len(parts) + 1)]


def _by_last_component(pkg_files: dict[str, bytes], name: str) -> list[str]:
    return sorted(p for p in pkg_files
                  if p.endswith(f"/{name}.py") or p.endswith(f"/{name}/__init__.py"))


def flat_source(name: str, rel: str, pkg_files: dict[str, bytes], package: str,
                flat_names: dict[str, str], overrides: dict[str, dict]) -> tuple[bytes, dict]:
    """Bytes of flat sibling `name` and how they were obtained."""
    if name in overrides:
        o = overrides[name]
        return o["bytes"], {"kind": "benchmark_sibling", "program_id": o["program_id"],
                            "benchmark_path": o["path"]}
    derived, changes = pv.flatten_imports(pkg_files[rel], package, flat_names)
    return derived, {"kind": "release_derived" if changes else "release_verbatim",
                     "rewritten_imports": changes}


def import_closure(target: bytes, pkg_files: dict[str, bytes], package: str,
                   renames: dict[str, str], target_stem: str = "",
                   overrides: dict[str, dict] | None = None) -> Closure:
    """Files and externals needed by `target` (benchmark module, imports flattened).
    A flat import of `target_stem` resolves to the benchmark module itself, never to the
    release copy."""
    cl = Closure()
    overrides = overrides or {}
    flat_names = {v: k for k, v in renames.items()}  # real 'types' -> flat 'types_renamed'
    todo: list[tuple[str, str, bytes]] = [("flat", "<target>", target)]  # (kind, origin, data)
    seen: set[tuple[str, str]] = set()

    def ext(name: str, origin: str, at_import: bool) -> None:
        cl.externals.setdefault(name, []).append({"imported_by": origin, "at_import_time": at_import})

    def add_pkg(path: str) -> None:
        for p in _parents(path) + [path]:
            if ("pkg", p) not in seen and p in pkg_files:
                seen.add(("pkg", p))
                cl.pkg_files.add(p)
                todo.append(("pkg", p, pkg_files[p]))

    def add_flat(name: str, origin: str) -> bool:
        if name == target_stem:
            return True
        real = renames.get(name, name)
        hits = _by_last_component(pkg_files, real)
        if not hits:
            return False
        if len(hits) > 1:
            cl.problems.append(f"flat import '{name}' from {origin} is ambiguous: {hits}")
            return True
        if ("flat", name) not in seen:
            seen.add(("flat", name))
            cl.flat_modules[name] = hits[0]
            data, _ = flat_source(name, hits[0], pkg_files, package, flat_names, overrides)
            todo.append(("flat", f"flat:{name}", data))
        return True

    while todo:
        kind, origin, data = todo.pop()
        here = origin if kind == "pkg" else None
        for node, at_import, optional in _imports(data):
            if isinstance(node, ast.ImportFrom) and node.level > 0:
                if kind != "pkg":
                    msg = f"relative import in flat module {origin}: {'.' * node.level}{node.module or ''}"
                    (cl.optional_unresolved if optional else cl.problems).append(msg)
                    continue
                base = here.split("/")[:-1]
                base = base[: len(base) - (node.level - 1)]
                dotted = ".".join(base + ([node.module] if node.module else []))
                f = _module_file(pkg_files, dotted)
                if f:
                    add_pkg(f)
                for a in node.names:
                    sub = _module_file(pkg_files, f"{dotted}.{a.name}")
                    if sub:
                        add_pkg(sub)
                if not f:
                    cl.problems.append(f"unresolvable relative import in {origin}: {dotted}")
                continue
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for mod in mods:
                top = mod.split(".")[0]
                if top == package:
                    f = _module_file(pkg_files, mod)
                    if f:
                        add_pkg(f)
                    else:
                        cl.problems.append(f"unresolvable package import in {origin}: {mod}")
                    if isinstance(node, ast.ImportFrom):
                        for a in node.names:
                            sub = _module_file(pkg_files, f"{mod}.{a.name}")
                            if sub:
                                add_pkg(sub)
                elif top in STDLIB_310:
                    continue
                elif kind == "flat" and "." not in mod and add_flat(mod, origin):
                    continue
                elif kind == "flat" and "." in mod and _module_file(pkg_files, f"{package}.{mod}"):
                    cl.problems.append(f"dotted flat import '{mod}' in {origin} (unsupported layout)")
                elif top == "__init__":
                    cl.problems.append(f"flat import of the package __init__ in {origin}")
                elif optional:
                    cl.optional_unresolved.append(f"{origin}: {mod}")
                else:
                    ext(top, origin, at_import)
    return cl


# ---------------------------------------------------------------- materialization

def materialize(sample: str, target_name: str, target: bytes, pkg_files: dict[str, bytes],
                closure: Closure, package: str, renames: dict[str, str] | None = None,
                overrides: dict[str, dict] | None = None, dest_root: Path = CONTEXTS_DIR) -> dict:
    """Write pkgroot/ and flat/ for one sample; returns the file manifest with hashes."""
    flat_names = {v: k for k, v in (renames or {}).items()}
    dest = dest_root / sample
    if dest.exists():
        shutil.rmtree(dest)
    files = []
    for rel in sorted(closure.pkg_files):
        p = dest / "pkgroot" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pkg_files[rel])
        files.append({"path": f"pkgroot/{rel}", "kind": "release_verbatim", "source": rel,
                      "sha256": pv.sha256(pkg_files[rel])})
    flat = dest / "flat"
    flat.mkdir(parents=True)
    if Path(target_name).stem in closure.flat_modules:
        raise ValueError(f"flat module would overwrite the benchmark module {target_name}")
    (flat / target_name).write_bytes(target)
    files.append({"path": f"flat/{target_name}", "kind": "benchmark_module",
                  "sha256": pv.sha256(target)})
    for name, rel in sorted(closure.flat_modules.items()):
        data, how = flat_source(name, rel, pkg_files, package, flat_names, overrides or {})
        (flat / f"{name}.py").write_bytes(data)
        files.append({"path": f"flat/{name}.py", "source": rel, "source_sha256": pv.sha256(pkg_files[rel]),
                      "sha256": pv.sha256(data), **how})
    return {"root": str(dest), "cwd": str(flat), "sys_path": [str(dest / "pkgroot")], "files": files}


# ---------------------------------------------------------------- per-project resolution

def sibling_overrides(per_sample: dict, rows: dict, current: str, common: set[str],
                      repo: Path) -> dict[str, dict]:
    """Flattened copies of other modules of the same project present in the snapshot whose
    matching releases include the whole release set (verified under normalization N)."""
    out = {}
    for s, info in per_sample.items():
        if s == current or not common <= set(info["matching_releases"]):
            continue
        path = rows[s]["target"]
        out[Path(path).stem] = {"program_id": rows[s]["program_id"], "path": path,
                                "bytes": (repo / path).read_bytes()}
    return out


def resolve_project(name: str, proj: dict, rows: dict[str, dict], arts: list[dict],
                    repo: Path = paths.REPO_ROOT) -> dict:
    package, renames = proj["package"], proj.get("module_renames", {})
    versions = {a["filename"]: a["version"] for a in arts}
    contents = {a["filename"]: pv.package_files(pv.archive_members(DIST_DIR / proj["pypi"] / a["filename"]),
                                                package) for a in arts}
    per_sample = {}
    for s in proj["samples"]:
        r = rows[s]
        target = (repo / r["target"]).read_bytes()
        m = sample_matches(target, Path(r["target"]).name, contents, versions, package, renames)
        per_sample[s] = {"status_before": r["status"], "matching_releases": sorted(m),
                         "matches": m}
    common = set.intersection(*(set(v["matching_releases"]) for v in per_sample.values()))
    result = {"project": name, "pypi": proj["pypi"], "package": package, "evidence": proj["evidence"],
              "release_set": sorted(common), "samples": {}, "_per_sample": per_sample}
    for s, info in per_sample.items():
        r = rows[s]
        decision = {"program_id": r["program_id"], "static_status": r["status"],
                    "matching_releases": info["matching_releases"], "matches": info["matches"]}
        result["samples"][s] = decision
        if r["status"] != manifest.PENDING_CONTEXT:
            decision["decision"] = "CROSS_CHECK_ONLY"
            continue
        if not info["matching_releases"]:
            decision.update(decision=UNRESOLVED_NO_MATCH,
                            reason="no released file equals the benchmark module under normalization N")
            continue
        if proj.get("vcs_snapshot"):
            decision.update(decision=UNRESOLVED_VCS,
                            reason=proj["vcs_snapshot"] + "; a matching release does not establish the "
                            "revision of the sibling modules")
            continue
        if not common:
            decision.update(decision=UNRESOLVED_NO_COMMON,
                            reason="no single release matches all samples of the project")
            continue
        target = (repo / r["target"]).read_bytes()
        candidates = [a for a in sorted(contents) if versions[a] in common]
        stem = Path(r["target"]).stem
        overrides = sibling_overrides(per_sample, rows, s, common, repo)
        decision["benchmark_siblings_available"] = sorted(overrides)
        closures = {a: import_closure(target, contents[a], package, renames, stem, overrides)
                    for a in candidates}
        needed = {a: sorted(c.pkg_files | set(c.flat_modules.values())) for a, c in closures.items()}
        signatures = {a: {f: pv.sha256(contents[a][f]) for f in needed[a]} for a in candidates}
        distinct = {json.dumps(sig, sort_keys=True) for sig in signatures.values()}
        decision["release_artifacts_checked"] = candidates
        if len(distinct) != 1:
            decision.update(decision=UNRESOLVED_AMBIGUOUS,
                            reason="required files differ between the artifacts of the release set",
                            per_artifact=signatures)
            continue
        art = candidates[0]
        cl = closures[art]
        if cl.problems:
            decision.update(decision=UNRESOLVED_CLOSURE, reason="; ".join(cl.problems))
            continue
        decision.update(decision=RESOLVED, release_set=sorted(common), artifact_used=art,
                        required_files=signatures[art],
                        flat_modules=cl.flat_modules, externals=cl.externals,
                        optional_unresolved=cl.optional_unresolved)
    return result


def resolve(repo: Path = paths.REPO_ROOT) -> Path:
    integrity.assert_originals_intact()
    rows = {r["name"]: r for r in manifest.read_manifest(paths.MANIFEST_CSV) if r["set"] == "p2"}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_DIR / stamp
    out.mkdir(parents=True)
    results = {}
    for name, proj in load_projects().items():
        arts = fetch(proj["pypi"], out)
        res = resolve_project(name, proj, rows, arts, repo)
        for s, d in res["samples"].items():
            if d.get("decision") == RESOLVED:
                art = d["artifact_used"]
                files = pv.package_files(pv.archive_members(DIST_DIR / proj["pypi"] / art), proj["package"])
                target = (repo / rows[s]["target"]).read_bytes()
                ov = sibling_overrides(res["_per_sample"], rows, s, set(res["release_set"]), repo)
                cl = import_closure(target, files, proj["package"], proj.get("module_renames", {}),
                                    Path(rows[s]["target"]).stem, ov)
                d["context"] = materialize(s, Path(rows[s]["target"]).name, target, files, cl,
                                           proj["package"], proj.get("module_renames", {}), ov)
        res.pop("_per_sample", None)
        results[name] = res
    (out / "resolution.json").write_text(json.dumps(results, indent=1, sort_keys=True, default=list),
                                         encoding="utf-8")
    integrity.assert_originals_intact()
    return out


def provenance_report(stamp: str) -> Path:
    """reports/A5_provenance.md: per-sample release matches with both hashes (generated)."""
    data = json.loads((OUT_DIR / stamp / "resolution.json").read_text(encoding="utf-8"))
    L = ["# A5 — p2 provenance: release matches and hashes\n",
         f"Generated by `python3 -m cleanroom.p2_context report --resolution {stamp}` from "
         f"`runs/p2_context/{stamp}/resolution.json`. Normalization N and derivation F are defined in "
         "`src/cleanroom/provenance.py`. For each sample, one matching member per release is shown "
         "(all members are in resolution.json). *raw* = byte-identical; *N* = identical after "
         "normalization N only.\n"]
    for project, pres in data.items():
        L.append(f"## {project} (package `{pres['package']}`)\n")
        L.append(f"Hypothesis evidence: {pres['evidence']}  ")
        L.append(f"Release set (intersection over the project's samples): "
                 f"{', '.join(pres['release_set']) or 'none'}\n")
        L.append("| Sample | Decision | Release | Artifact :: member | Match | Benchmark SHA-256 | Release SHA-256 |")
        L.append("|---|---|---|---|---|---|---|")
        for s, d in pres["samples"].items():
            matches = d.get("matches", {})
            if not matches:
                L.append(f"| `{d['program_id']}` | `{d.get('decision')}` | — | no match | — | — | — |")
                continue
            for v in sorted(matches):
                m = matches[v][0]
                L.append(f"| `{d['program_id']}` | `{d.get('decision')}` | {v} | `{m['artifact']}` :: "
                         f"`{m['member']}` | {'raw' if m['raw_equal'] else 'N'} | "
                         f"`{m['benchmark_sha256'][:16]}…` | `{m['release_sha256'][:16]}…` |")
        L.append("")
        changed = {d["program_id"]: next(iter(d["matches"].values()))[0]["changed_imports"]
                   for d in pres["samples"].values() if d.get("matches")}
        if any(changed.values()):
            L.append("Import statements that differ before normalization (release → benchmark):\n")
            for pid, ch in changed.items():
                for old, new in ch:
                    L.append(f"- `{pid}`: `{old}` → `{new}`")
            L.append("")
    out = paths.REPORTS_DIR / "A5_provenance.md"
    out.write_text("\n".join(L), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="cleanroom.p2_context")
    ap.add_argument("cmd", choices=["resolve", "report"])
    ap.add_argument("--resolution", help="run stamp (for report)")
    args = ap.parse_args(argv)
    if args.cmd == "report":
        print(provenance_report(args.resolution).relative_to(paths.CLEANROOM))
        return 0
    out = resolve()
    data = json.loads((out / "resolution.json").read_text(encoding="utf-8"))
    for proj in data.values():
        for s, d in proj["samples"].items():
            if d.get("decision") != "CROSS_CHECK_ONLY":
                print(f"{d['program_id']:12} {proj['project']:20} {d['decision']:32} "
                      f"releases={proj['release_set']} {d.get('reason', '')[:80]}")
    print(f"output: {out.relative_to(paths.CLEANROOM)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
