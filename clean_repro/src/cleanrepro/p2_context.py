"""Rebuild the project context of the p2 modules (100_300 LOC p2) and validate the saved suites.

The repository holds, per sample, the authors' flattened copy of the module under test (in
"pynguin coverage/sampleN") and the saved Pynguin and ChatGPT suites with their coverage reports,
but not the sibling project files the module imports.  The saved reports list those siblings
(e.g. __init__.py, moduleutils.py) and, for a few samples, absolute paths into the authors'
checkouts (httpie "cli-master", "pdir2-0.3.2", "flutes_new").

Procedure (all logged to data/p2_projects.csv):
 1. Each sample is mapped to its PyPI project by module and sibling names (PROJECTS below).
 2. Every release of that project uploaded before the first repository commit (2024-01-26) is
    downloaded; the module file of each release is compared with the authors' copy after
    normalising relative imports ("from .x import" -> "from x import"), comments and blank lines.
    The release with an identical normalised text is chosen (latest if several); if none is
    identical, the most similar release is chosen and the sample is flagged.
 3. Sandbox = the authors' module copy (unchanged) + the sibling files named in the saved reports,
    taken from the chosen release with relative imports flattened the same way.
 4. Saved Pynguin and ChatGPT suites are re-run there; results are compared with saved reports.
"""
from __future__ import annotations

import csv
import difflib
import io
import json
import re
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from . import covreport, execute, sandbox
from .paths import CACHE, DATA, REPO, env_python

CUTOFF = "2024-01-26"
PYPI = "https://pypi.org/pypi/{}/json"

# sample number -> (PyPI project, package directory inside the distribution)
PROJECTS: dict[int, tuple[str, str]] = {
    **{n: ("flutils", "flutils") for n in range(1, 7)},
    7: ("codetiming", "codetiming"),
    **{n: ("httpie", "httpie") for n in range(8, 13)},
    **{n: ("pymonet", "pymonet") for n in range(13, 22)},
    22: ("python-string-utils", "string_utils"), 23: ("python-string-utils", "string_utils"),
    24: ("sty", "sty"),
    **{n: ("typesystem", "typesystem") for n in range(25, 33)},
    **{n: ("docstring-parser", "docstring_parser") for n in range(33, 37)},
    **{n: ("dataclasses-json", "dataclasses_json") for n in range(37, 40)},
    40: ("pdir2", "pdir"), 41: ("pdir2", "pdir"),
    42: ("flutes", "flutes"), 43: ("flutes", "flutes"),
}


# ---------------------------------------------------------------- downloads
def releases(project: str) -> list[tuple[str, str, str]]:
    """[(version, upload_date, url)] for releases before CUTOFF, sdist preferred over wheel."""
    cache = CACHE / "pypi" / f"{project}.json"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(urllib.request.urlopen(PYPI.format(project), timeout=60).read())
    meta = json.loads(cache.read_text())
    out = []
    for ver, files in meta["releases"].items():
        if not files or files[0]["upload_time"][:10] >= CUTOFF:
            continue
        sd = [f for f in files if f["packagetype"] == "sdist"]
        wh = [f for f in files if f["packagetype"] == "bdist_wheel"]
        f = (sd or wh or [None])[0]
        if f:
            out.append((ver, f["upload_time"][:10], f["url"]))
    return sorted(out, key=lambda r: r[1])


def fetch(url: str) -> Path:
    p = CACHE / "dists" / url.rsplit("/", 1)[1]
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(urllib.request.urlopen(url, timeout=120).read())
    return p


def package_files(dist: Path, pkg: str) -> dict[str, str]:
    """{relative path inside the package dir: text} for every .py file of `pkg` in a dist."""
    out: dict[str, str] = {}
    pat = re.compile(rf"(?:^|/){re.escape(pkg)}/(.+\.py)$")
    if dist.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(dist) as tf:
            for m in tf.getmembers():
                mm = pat.search(m.name)
                if mm and m.isfile() and "/tests/" not in "/" + mm[1]:
                    out.setdefault(mm[1], tf.extractfile(m).read().decode("utf-8", "replace"))
    else:
        with zipfile.ZipFile(dist) as zf:
            for n in zf.namelist():
                mm = pat.search(n)
                if mm:
                    out.setdefault(mm[1], zf.read(n).decode("utf-8", "replace"))
    return out


# ---------------------------------------------------------------- normalisation
_REL_FROM = re.compile(r"^(\s*)from\s+\.+([\w.]*)\s+import\s+", re.M)


def flatten_imports(text: str) -> str:
    """'from .x import y' -> 'from x import y';  'from . import y' -> 'import y' (flat layout)."""
    def sub(m: re.Match) -> str:
        indent, mod = m[1], m[2]
        return f"{indent}from {mod} import " if mod else f"{indent}import "
    return _REL_FROM.sub(sub, text)


def flatten_for_sandbox(text: str, pkg: str, siblings: set[str], renames: dict[str, str],
                        here: str = "") -> str:
    """Flat-layout rewrite of a project file, following the conventions visible in the authors'
    own module copies (e.g. httpie config.py: 'from __init__ import __version__ #.',
    'from compat import is_windows'; flutes: types.py renamed to types_renamed.py).

    Relative and absolute self-package imports are first resolved to a path from the package
    root ('here' = subpackage of the file, '' for top level), then:
      top-level module x           -> 'from x import ...' / 'import x'
      module in a subpackage a.b   -> 'a.b' (if 'b.py' was copied flat as a sibling: 'b')
      the package itself           -> 'import y' for sibling modules y, else
                                      'from __init__ import y' (names defined in __init__)
    `renames` maps original module names to renamed files (types -> types_renamed)."""
    def resolve(dots: str, mod: str) -> str | None:
        """Module path from the package root ('' = the package itself); None = not ours."""
        if not dots:
            if mod != pkg and not mod.startswith(pkg + "."):
                return None
            return mod[len(pkg):].lstrip(".")
        base = here.split(".") if here else []
        up = len(dots) - 1
        base = base[:len(base) - up] if up else base
        return ".".join(base + ([mod] if mod else []))

    def name(path: str) -> str:
        parts = path.split(".")
        if len(parts) > 1 and parts[-1] + ".py" in siblings:      # subpackage file copied flat
            return renames.get(parts[-1], parts[-1])
        parts[0] = renames.get(parts[0], parts[0])
        return ".".join(parts)

    def sub_from(m: re.Match) -> str:
        indent, dots, mod, names = m[1], m[2], m[3], m[4]
        path = resolve(dots, mod)
        if path is None:
            return m[0]
        if path:
            return f"{indent}from {name(path)} import {names}"
        items = [n.strip() for n in names.strip("()").split(",") if n.strip()]
        if items and all(i.split(" as ")[0].strip() + ".py" in siblings for i in items):
            return f"{indent}import {', '.join(name(i) for i in items)}"
        return f"{indent}from __init__ import {names}"

    def sub_import(m: re.Match) -> str:
        path = resolve("", m[2])
        return m[0] if not path else f"{m[1]}import {name(path)}"
    text = re.sub(r"^(\s*)from\s+(\.*)([\w.]*)\s+import\s+(.+)$", sub_from, text, flags=re.M)
    text = re.sub(rf"^(\s*)import\s+({re.escape(pkg)}\.[\w.]+)", sub_import, text, flags=re.M)
    return text


def normalise(text: str) -> list[str]:
    out = []
    for line in flatten_imports(text).splitlines():
        line = re.sub(r"\s+#.*$", "", line).rstrip()
        if line.strip() and not line.lstrip().startswith("#"):
            out.append(line)
    return out


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalise(a), normalise(b), autojunk=False).ratio()


# ---------------------------------------------------------------- matching
def score_matrix(rows: list[dict]) -> dict[str, dict[str, dict]]:
    """{sample: {version: {similarity, path, date, url}}} over all releases of its project."""
    out: dict[str, dict[str, dict]] = {}
    for row in rows:
        project, pkg = PROJECTS[int(row["name"][6:])]
        module_text = (REPO / row["module_path"]).read_text(errors="replace")
        out[row["name"]] = {}
        for ver, date, url in releases(project):
            files = package_files(fetch(url), pkg)
            cands = [k for k in files if Path(k).name == row["module_file"]]
            if cands:
                k = max(cands, key=lambda c: similarity(module_text, files[c]))
                out[row["name"]][ver] = {"similarity": similarity(module_text, files[k]),
                                         "path": k, "date": date, "url": url}
    return out


def match_all(rows: list[dict]) -> list[dict]:
    """One release per project: the release with the most samples identical after normalisation,
    then the highest mean similarity, then the latest date.  All samples of a project share that
    release so that sibling files are mutually consistent.  The per-sample best release is
    recorded alongside for transparency."""
    m = score_matrix(rows)
    by_project: dict[str, list[str]] = {}
    for row in rows:
        by_project.setdefault(PROJECTS[int(row["name"][6:])][0], []).append(row["name"])
    results = []
    for project, samples in by_project.items():
        versions = set.intersection(*(set(m[s]) for s in samples))
        def key(v):
            sims = [m[s][v]["similarity"] for s in samples]
            return (sum(x == 1.0 for x in sims), sum(sims) / len(sims), m[samples[0]][v]["date"])
        chosen = max(versions, key=key)
        for s in samples:
            row = next(r for r in rows if r["name"] == s)
            c = m[s][chosen]
            best_v = max(m[s], key=lambda v: (m[s][v]["similarity"], m[s][v]["date"]))
            results.append({"sample": s, "module_file": row["module_file"], "project": project,
                            "package": PROJECTS[int(s[6:])][1], "version": chosen,
                            "upload_date": c["date"], "path_in_package": c["path"],
                            "similarity": round(c["similarity"], 4),
                            "identical_after_normalisation": c["similarity"] == 1.0,
                            "best_single_version": best_v,
                            "best_single_similarity": round(m[s][best_v]["similarity"], 4),
                            "dist_url": c["url"], "dist_sha256": _sha(fetch(c["url"]))})
            print(s, project, chosen, round(c["similarity"], 4), "| best alone:", best_v,
                  round(m[s][best_v]["similarity"], 4), flush=True)
    return results


def _sha(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_projects(results: list[dict]) -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    p = DATA / "p2_projects.csv"
    keys = []
    for r in results:
        keys += [k for k in r if k not in keys]
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(results)
    return p


if __name__ == "__main__":
    from .validate_baselines import load_manifest
    rows = [r for r in load_manifest() if r["group"] == "p2"]
    print(write_projects(match_all(rows)))


# ---------------------------------------------------------------- sandboxes and validation
def load_projects() -> dict[str, dict]:
    return {r["sample"]: r for r in csv.DictReader(open(DATA / "p2_projects.csv"))}


def dist_tree(url: str) -> dict[str, str]:
    """{path relative to the distribution root: text} for every text file of a distribution."""
    dist = fetch(url)
    out: dict[str, str] = {}
    if dist.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(dist) as tf:
            for m in tf.getmembers():
                if m.isfile() and m.name.endswith(".py"):
                    out[m.name.split("/", 1)[1] if "/" in m.name else m.name] = \
                        tf.extractfile(m).read().decode("utf-8", "replace")
    else:
        with zipfile.ZipFile(dist) as zf:
            for n in zf.namelist():
                if n.endswith(".py"):
                    out[n] = zf.read(n).decode("utf-8", "replace")
    return out


def report_files(row: dict, keys: tuple[str, ...] = ("pynguin_stmt_report", "chatgpt_stmt_report")) -> list[str]:
    """Non-test file names listed in the given saved reports (relative or absolute)."""
    names: list[str] = []
    for key in keys:
        if row.get(key):
            for n in covreport.parse_text_report((REPO / row[key]).read_text(errors="replace")):
                if Path(n).name.startswith("test_") and not n.startswith("/"):
                    continue
                if n not in names:
                    names.append(n)
    return names


def saved_stmts(row: dict, keys: tuple[str, ...] | None, name: str) -> int | None:
    for key in keys or ("pynguin_stmt_report", "chatgpt_stmt_report"):
        if row.get(key):
            r = covreport.parse_text_report((REPO / row[key]).read_text(errors="replace")).get(name)
            if r is not None:
                return r.stmts
    return None


CHECKOUT = re.compile(r"^/Users/DELL/Desktop/python_projects_pynguin_testing/[^/]+/(?P<pkg>[^/]+)/(?P<sub>.+)$")


def build_context(row: dict, proj: dict, sb: Path, report_keys: tuple[str, ...] | None = None) -> dict:
    """Copy the authors' module and the context files into sandbox `sb`.

    Relative names in the saved reports were files next to the tests (flat layout); absolute names
    were files of a project checkout outside the test folder.  Rules (each application is logged):
      R1 the module under test (relative) is the authors' copy, unchanged
      R2 a relative sibling found in the package is copied flattened (flatten_for_sandbox)
      R3 a relative 'X_renamed.py' whose 'X.py' exists in the package is copied flattened under
         the new name, and imports of X in all flattened files point to X_renamed
      R6 a relative file whose saved report row has 0 statements is written empty (the authors'
         test folders contained empty __init__.py files); checked before R2
      R2b a relative sibling not at the package top level but found once by basename in a
         subpackage (typesystem tokenize/*.py) is copied flat and flattened
      R4 a relative file found in the project's tests/ directory is copied unchanged
      R5 an absolute checkout file '<checkout>/<pkg>/<sub>' is copied, flattened like the authors'
         module copies (their copies of checkout modules use flat imports), to '_ctx/<pkg>/<sub>';
         '_ctx' is put on PYTHONPATH (package imports such as 'from pdir.api import ...') and
         '_ctx/<pkg>' is appended at the END of sys.path (flat imports such as
         'from _internal_utils import ...'), via '_ctx_site/sitecustomize.py'.  Appending, not
         prepending, keeps a checkout file named like a stdlib module (flutes/types.py) from
         shadowing the stdlib, which the authors' runs evidently did not suffer from.
    """
    log = {"rules": {}, "missing": [], "pythonpath": [], "append_path": []}
    tree = dist_tree(proj["dist_url"])
    pkg = proj["package"]
    pkg_files = {k.split(f"{pkg}/", 1)[1]: v for k, v in tree.items()
                 if f"{pkg}/" in k and "/tests/" not in "/" + k}
    test_files = {k.split("tests/", 1)[1]: v for k, v in tree.items() if k.startswith("tests/")}
    names = report_files(row, report_keys) if report_keys else report_files(row)
    renames = {n[:-len("_renamed.py")]: n[:-3] for n in report_files(row)
               if n.endswith("_renamed.py") and n[:-len("_renamed.py")] + ".py" in pkg_files}
    siblings = {Path(n).name for n in names if not n.startswith("/")} | {f + ".py" for f in renames}
    for n in names:
        m = CHECKOUT.match(n)
        if m:
            sub = m["sub"]
            src = pkg_files.get(sub) if m["pkg"] == pkg else None
            if src is None:
                log["missing"].append(n)
                continue
            dst = sb / "_ctx" / m["pkg"] / sub
            dst.parent.mkdir(parents=True, exist_ok=True)
            top = {k for k in pkg_files if "/" not in k} | {f + ".py" for f in renames}
            here = ".".join(Path(sub).parent.parts)
            # the package __init__ keeps its relative imports so that 'import <pkg>' still works
            dst.write_text(src if sub == "__init__.py" else
                           flatten_for_sandbox(src, pkg, top, renames, here))
            stem = Path(sub).stem
            if "/" not in sub and stem in renames:      # R3 for checkout files
                (dst.parent / f"{renames[stem]}.py").write_text(
                    flatten_for_sandbox(src, pkg, top, renames, here))
            log["rules"][n] = "R5"
            if "_ctx" not in log["pythonpath"]:
                log["pythonpath"].append("_ctx")
            if f"_ctx/{m['pkg']}" not in log["append_path"]:
                log["append_path"].append(f"_ctx/{m['pkg']}")
        elif n == row["module_file"]:
            continue
        elif saved_stmts(row, report_keys, n) == 0:
            (sb / n).parent.mkdir(parents=True, exist_ok=True)
            (sb / n).write_text("")
            log["rules"][n] = "R6 (saved report: 0 statements -> empty file)"
        elif n in pkg_files:
            (sb / n).parent.mkdir(parents=True, exist_ok=True)
            (sb / n).write_text(flatten_for_sandbox(pkg_files[n], pkg, siblings, renames))
            log["rules"][n] = "R2"
        elif n.endswith("_renamed.py") and n[:-len("_renamed.py")] + ".py" in pkg_files:
            (sb / n).write_text(flatten_for_sandbox(pkg_files[n[:-len("_renamed.py")] + ".py"],
                                                    pkg, siblings, renames))
            log["rules"][n] = "R3"
        elif "/" not in n and len([k for k in pkg_files if Path(k).name == n]) == 1:
            k = next(k for k in pkg_files if Path(k).name == n)
            (sb / n).write_text(flatten_for_sandbox(pkg_files[k], pkg, siblings, renames,
                                                    ".".join(Path(k).parent.parts)))
            log["rules"][n] = f"R2b ({k})"
        elif n in test_files:
            (sb / n).parent.mkdir(parents=True, exist_ok=True)
            (sb / n).write_text(test_files[n])
            log["rules"][n] = "R4"
        else:
            log["missing"].append(n)
    if log["append_path"]:
        site = sb / "_ctx_site"
        site.mkdir()
        site.joinpath("sitecustomize.py").write_text(
            "import sys\n" + "".join(f"sys.path.append({str(sb / p)!r})\n" for p in log["append_path"]))
        log["pythonpath"].append("_ctx_site")
    # R1 last, so that the authors' copy is never overwritten by a release file
    if not any(Path(n).name == row["module_file"] and n.startswith("/") for n in names) or \
            row["module_file"] in names:
        sandbox.copy_in(row["module_path"], sb, row["module_file"])
        log["rules"][row["module_file"]] = "R1"
    return log


def validate() -> None:
    from .validate_baselines import OUT, compare, load_manifest, reproduced_row, write_csv
    py = env_python("p2")
    projects = load_projects()
    rows_out, ctx_logs = [], {}
    for row in load_manifest():
        if row["group"] != "p2":
            continue
        s, mod = row["name"], row["module_file"]
        proj = projects[s]
        for suite, test_key, reports in (
                ("pynguin(saved)", "pynguin_suite", ("pynguin_stmt_report", "pynguin_branch_report")),
                ("chatgpt(saved)", "chatgpt_suite", ("chatgpt_stmt_report", "chatgpt_branch_report"))):
            if not row[test_key]:
                continue
            tag = suite.split("(")[0]
            sb = sandbox.fresh("baseline", "p2", s, tag)
            # context = files listed in this suite's own saved report (the other suite's if none)
            own = (reports[0],) if row[reports[0]] else None
            ctx_logs[f"{s}/{tag}"] = build_context(row, proj, sb, own)
            test_name = Path(row[test_key]).name
            sandbox.copy_in(row[test_key], sb, test_name)
            out = OUT / "logs" / "p2" / s / tag
            pp = ctx_logs[f"{s}/{tag}"]["pythonpath"]
            env = {"PYTHONPATH": ":".join(str(sb / p) for p in pp)} if pp else None
            summ = execute.run_both(sb, [test_name], mod, py, out, extra_env=env)
            for mode, rep in zip(("stmt", "branch"), reports):
                saved = covreport.read_text_report(REPO / row[rep], mod) if row[rep] else None
                r = {"sample_id": row["sample_id"], "category_derived": row["category"],
                     "suite": suite, "suite_is_pynguin": row["pynguin_suite_is_pynguin"] if tag == "pynguin" else "",
                     "project": proj["project"], "version": proj["version"], "mode": mode}
                r.update(compare(saved, reproduced_row(out, mode, mod), mode == "branch"))
                r.update(collected=summ["collected"], passed=summ["passed"], failed=summ["failed"],
                         errors=summ["errors"], collection_error=summ["collection_error"],
                         missing_context=";".join(ctx_logs[f"{s}/{tag}"]["missing"]))
                rows_out.append(r)
        print(s, "done", flush=True)
    write_csv("p2_rerun.csv", rows_out)
    (OUT / "p2_context_log.json").write_text(json.dumps(ctx_logs, indent=1))


def package_module_names(proj: dict) -> set[str]:
    """Module names of the project (all files of the release's package); used so that the
    extraction never redirects an import of a real project module to the module under test."""
    pkg = proj["package"]
    names = {pkg}
    for k in dist_tree(proj["dist_url"]):
        if f"{pkg}/" in k:
            names.add(Path(k).stem)
    return names - {"__init__"}
