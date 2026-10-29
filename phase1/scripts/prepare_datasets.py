"""Make the large code samples runnable: rebuild the projects they come from, with the authors' import layout.

    .venv/bin/python scripts/prepare_datasets.py p2      # 100_300 LOC p2 (43 modules, 11 projects)
    .venv/bin/python scripts/prepare_datasets.py p1      # 100_300 LOC p1 (41 modules, 16 repositories)

p1 (README: "used for generating results of iterative improvement", Table 3). Each module names its GitHub source in
its first line (or in cat*/a.txt). The repository is cloned (blobs on demand) and taken as it was at the cutoff date
if the file there equals the authors' module apart from comments and imports, else at the last such commit. Its .py
files go to datasets/p1/src/<owner>__<repo>@<commit>/; the module's directory, the repository root (and src/) are
put on the path, after an overlay of the authors' own copies of project files (helper files in the sample folders,
other samples of the same directory). Third-party packages go to datasets/p1/deps (optional heavy ones tried one by
one). A module that still cannot be imported is run anyway (0 % coverage for every tool) and the reason is recorded.

p2 ("taken from benchmark data used by Lukasczyk et al.", repository ReadMe). Every module is identical, apart from
its import lines, to a file of a PyPI release; the release is found by comparing all releases up to January 2024
(the repository's date). The authors ran each module inside its package directory with the package's own imports
flattened: `from httpie.cookies import X` -> `from cookies import X`, `from . import __version__` ->
`from __init__ import __version__`, `from typesystem.tokenize.tokens import X` -> `from tokens import X` (subpackage
named like a standard module), flutes/types.py -> types_renamed.py (module named like a standard module).
This script rebuilds that layout for the other files of the package, from the matching release:

    datasets/p2/archives/              downloaded releases (sha256 checked against PyPI)
    datasets/p2/src/<dist>-<version>/  the package directory, imports flattened the same way
    datasets/p2/deps/                  the releases themselves and their dependencies (uv pip install --target)
    datasets/p2/manifest.json          versions, candidates, renames, per-module category and import check (tracked)

The module under test always comes from the repository (the authors' file): it sits in the work directory, which
is first on sys.path, so it shadows the rebuilt copy and every other file imports that one copy. At run time the
pipeline appends the deps directory (as a site directory) and the package directory to sys.path through two
environment variables read by a .pth hook installed in both venvs (see install_hook).
"""
import argparse
import ast
import concurrent.futures as cf
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from common import PHASE1, PYNGUIN_BIN, REPO, VENV_PY, atomic_write_json, now_iso

DATASETS = PHASE1 / "datasets"
STD = set(sys.stdlib_module_names)
CUTOFF = "2024-01-31"          # the repository was uploaded on 2024-01-27
EXCLUDE_NEWER = "2026-10-11"   # same rule as env/*.lock
HOOK = ('import os, site, sys; [site.addsitedir(p) for p in os.environ.get("PHASE1_SITE_DIRS", "").split(os.pathsep) if p]; '
        'sys.path.extend(p for p in os.environ.get("PHASE1_PATH_APPEND", "").split(os.pathsep) if p)\n')

P2_DIR = REPO / "100_300 LOC p2" / "pynguin coverage"
P2_DISTS = {  # sample number -> (PyPI distribution, package directory)
    **{i: ("flutils", "flutils") for i in range(1, 7)}, 7: ("codetiming", "codetiming"),
    **{i: ("httpie", "httpie") for i in range(8, 13)}, **{i: ("pymonet", "pymonet") for i in range(13, 22)},
    22: ("python-string-utils", "string_utils"), 23: ("python-string-utils", "string_utils"), 24: ("sty", "sty"),
    **{i: ("typesystem", "typesystem") for i in range(25, 33)},
    **{i: ("docstring-parser", "docstring_parser") for i in range(33, 37)},
    **{i: ("dataclasses-json", "dataclasses_json") for i in range(37, 40)}, 40: ("pdir2", "pdir"), 41: ("pdir2", "pdir"),
    42: ("flutes", "flutes"), 43: ("flutes", "flutes")}
# optional dependencies the modules import (typesystem: tokenize_yaml / forms; flutes: exception; pdir: api)
P2_EXTRAS = ["pyyaml", "jinja2", "ipython", "colorama"]
# where the authors' module differs from the flattening rule (their file is used as it is)
P2_NOTES = {
    "sample4": "authors rewrote `from flutils.codecs import register_codecs` to `from codecs import ...`, which hits the "
               "standard module codecs: convert_escaped_utf8_literal() raises ImportError (kept as in their file)",
    "sample5": "authors left `from .decorators import cached_property` in a branch for Python < 3.8 (never executed)",
    **{f"sample{i}": "authors left pymonet's lazy imports package-absolute (`from pymonet.maybe import Maybe` inside "
                     "methods): they use the installed release in deps/" for i in (13, 14, 16, 17, 20)},
}


# ----------------------------------------------------------------------------- generic helpers

def structural_category(src):
    """The paper's categories applied to the module: any top-level class -> 3, else any function -> 2, else 1."""
    body = ast.parse(src).body
    if any(isinstance(n, ast.ClassDef) for n in body):
        return "cat3_classes"
    if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in body):
        return "cat2_functions"
    return "cat1_scripts"


class _StripImports(ast.NodeTransformer):
    def visit_Import(self, n):
        return None

    visit_ImportFrom = visit_Import


def without_imports(src):
    """Source with every import statement removed and formatting normalised (comparison key)."""
    try:
        tree = _StripImports().visit(ast.parse(src))
    except SyntaxError:
        return None
    return ast.unparse(ast.fix_missing_locations(tree))


def fetch(url, dest, sha256=None):
    if not dest.exists():
        data = urllib.request.urlopen(url, timeout=120).read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
    if sha256 and hashlib.sha256(dest.read_bytes()).hexdigest() != sha256:
        dest.unlink()
        raise RuntimeError(f"sha256 mismatch: {url}")
    return dest


def archive_files(path):
    """{member name: bytes} of a .tar.gz / .zip / .whl, read in memory (nothing is extracted)."""
    out = {}
    if path.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path) as t:
            for m in t.getmembers():
                if m.isfile():
                    out[m.name] = t.extractfile(m).read()
    else:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if not n.endswith("/"):
                    out[n] = z.read(n)
    return out


def package_files(files, pkg):
    """{path relative to the package directory: bytes}, from the shortest <pkg>/ directory in the archive."""
    roots = sorted({n.split("/").index(pkg) for n in files if pkg in n.split("/")[:-1]})
    if not roots:
        return {}
    out = {}
    for n, data in files.items():
        parts = n.split("/")
        if len(parts) > roots[0] + 1 and parts[roots[0]] == pkg:
            rel = parts[roots[0] + 1:]
            if "tests" in rel[:-1] or "__pycache__" in rel or rel[-1].endswith(".pyc"):
                continue
            out["/".join(rel)] = data
    return out


def pypi_releases(dist):
    d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{dist}/json", timeout=60))
    out = []
    for ver, files in d["releases"].items():
        files = [f for f in files if f["upload_time"][:10] <= CUTOFF]
        pick = [f for f in files if f["packagetype"] == "bdist_wheel"] or [f for f in files if f["packagetype"] == "sdist"]
        if pick:
            f = pick[0]
            out.append({"version": ver, "date": f["upload_time"][:10], "url": f["url"], "filename": f["filename"],
                        "sha256": f["digests"]["sha256"]})
    return sorted(out, key=lambda r: r["date"])


# ----------------------------------------------------------------------------- the authors' import layout

class Layout:
    """Canonical (flattened) import name of every file of a package directory, the authors' rules:
    root module x.py -> x (x_renamed if x is a standard module name), root __init__.py -> __init__,
    sub/x.py -> sub.x, sub/__init__.py -> sub; if `sub` is a standard module name, sub/x.py -> x (sub/ goes on
    sys.path) and sub/__init__.py has no flat name (its imports stay as they are and use the installed release)."""

    def __init__(self, rel_paths, pkg):
        self.pkg = pkg
        self.files = {p for p in rel_paths if p.endswith(".py")}
        self.renamed = {p[:-3]: p[:-3] + "_renamed" for p in self.files if "/" not in p and p[:-3] in STD}
        self.flat_dirs = sorted({p.split("/")[0] for p in self.files if "/" in p and p.split("/")[0] in STD})

    def file_of(self, parts):
        """('module', path) / ('package', path) / None for a dotted path inside the package."""
        p = "/".join(parts)
        if parts and p + ".py" in self.files:
            return "module", p + ".py"
        if (p + "/__init__.py" if p else "__init__.py") in self.files:
            return "package", (p + "/__init__.py" if p else "__init__.py")
        return None

    def canonical(self, parts):
        if not parts:
            return "__init__"
        if parts[0] in self.flat_dirs:
            return parts[1] if len(parts) == 2 and self.file_of(parts) == ("module", "/".join(parts) + ".py") else None
        if len(parts) == 1 and parts[0] in self.renamed:
            return self.renamed[parts[0]]
        return ".".join(parts)

    def new_path(self, rel):
        stem = rel[:-3]
        return self.renamed[stem] + ".py" if stem in self.renamed else rel


def rewrite_imports(src, rel, layout):
    """Flatten the package's own imports in one file of the package (rel: its path in the package)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src, []
    here = rel.split("/")[:-1]   # package containing this file
    pkg = layout.pkg
    edits, log = [], []

    def target_parts(node):
        if node.level:
            base = here[:len(here) - (node.level - 1)] if node.level - 1 <= len(here) else None
            if base is None:
                return None
            return base + (node.module.split(".") if node.module else [])
        if node.module and (node.module == pkg or node.module.startswith(pkg + ".")):
            return node.module.split(".")[1:]
        return None

    for node in ast.walk(tree):
        new = None
        if isinstance(node, ast.ImportFrom) and node.module != "__future__":
            parts = target_parts(node)
            if parts is None or layout.file_of(parts) is None:
                continue
            stmts, names = [], []   # module imports; names imported from the module `parts` itself
            for a in node.names:
                sub = parts + [a.name]
                dotted = parts and layout.canonical(parts) and layout.canonical(sub) == f"{layout.canonical(parts)}.{a.name}"
                if a.name != "*" and layout.file_of(sub) and not dotted:  # `from legacy import mod` stays a from-import
                    canon = layout.canonical(sub)
                    if canon is None:
                        break
                    alias = a.asname or a.name
                    stmts.append(f"import {canon}" if canon == alias else f"import {canon} as {alias}")
                else:
                    names.append(a.name + (f" as {a.asname}" if a.asname else ""))
            else:
                if names:
                    canon = layout.canonical(parts)
                    if canon is None:
                        continue
                    stmts.insert(0, f"from {canon} import {', '.join(names)}")
                new = "; ".join(stmts)
        elif isinstance(node, ast.Import):
            stmts = []
            for a in node.names:
                mparts = a.name.split(".")
                if mparts[0] != pkg or len(mparts) == 1 or not a.asname:
                    break  # `import pkg.x` binds `pkg`: left as it is (installed release)
                canon = layout.canonical(mparts[1:])
                if canon is None or layout.file_of(mparts[1:]) is None:
                    break
                stmts.append(f"import {canon} as {a.asname}")
            else:
                new = "; ".join(stmts)
        if new is not None:
            edits.append((node.lineno, node.col_offset, node.end_lineno, node.end_col_offset, new))
    lines = src.splitlines(keepends=True)
    for l0, c0, l1, c1, new in sorted(edits, reverse=True):
        old = "".join(lines[l0 - 1:l1])
        start, end = c0, len(old) - (len(lines[l1 - 1]) - c1)
        log.append({"line": l0, "old": old[start:end], "new": new})
        merged = old[:start] + new + old[end:]
        lines[l0 - 1:l1] = [merged]
    return "".join(lines), sorted(log, key=lambda e: e["line"])


# ----------------------------------------------------------------------------- environment

def site_packages(py):
    return Path(subprocess.run([str(py), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
                               capture_output=True, text=True, check=True).stdout.strip())


def install_hook():
    """The .pth hook that appends PHASE1_SITE_DIRS (as site dirs: their .pth files run) and PHASE1_PATH_APPEND to
    sys.path. Appended, not prepended: the standard library and the venv's own packages always win, as they did
    in the authors' runs for every module already imported by Python itself."""
    out = []
    for py in (VENV_PY, PYNGUIN_BIN.parent / "python"):
        sp = site_packages(py)
        (sp / "phase1_paths.pth").write_text(HOOK)
        out.append(str(sp / "phase1_paths.pth"))
    return out


def runtime_env(entry):
    """Environment variables for one prepared program (paths relative to phase1/datasets in the manifest)."""
    return {"PHASE1_SITE_DIRS": os.pathsep.join(str(DATASETS / p) for p in entry["site_dirs"]),
            "PHASE1_PATH_APPEND": os.pathsep.join(str(DATASETS / p) for p in entry["path_append"])}


def import_check(module_file, module, env, data_files=()):
    """Import the module (the authors' file) in both venvs, in a fresh temporary directory, after pytest (main venv)
    or pynguin (Pynguin's venv) as in a real run (they import modules some old code relies on, e.g. collections.abc)."""
    res = {}
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(module_file, Path(tmp) / f"{module}.py")
        for f in data_files:
            shutil.copy(f, Path(tmp) / Path(f).name)
        for name, py, first in (("main", VENV_PY, "pytest"), ("pynguin", PYNGUIN_BIN.parent / "python", "pynguin")):
            try:
                p = subprocess.run([str(py), "-c", f"import {first}; import {module}"], cwd=tmp, capture_output=True,
                                   text=True, env={**os.environ, **env, "PYNGUIN_DANGER_AWARE": "1"},
                                   stdin=subprocess.DEVNULL, timeout=120)
            except subprocess.TimeoutExpired:
                res[name] = "import did not finish in 120 s (the module runs at import)"
                continue
            err = (p.stderr.strip().splitlines() or [""])[-1].replace(str(REPO) + "/", "")  # no machine paths
            res[name] = "ok" if p.returncode == 0 else err[:300]
    return res


def uv_install(target, reqs):
    cmd = ["uv", "pip", "install", "--python", str(VENV_PY), "--target", str(target), "--exclude-newer", EXCLUDE_NEWER, *reqs]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"dependency install failed:\n{' '.join(cmd)}\n{p.stderr[-3000:]}")
    return cmd


# ----------------------------------------------------------------------------- p2

def prepare_p2(force=False):
    out = DATASETS / "p2"
    if force:
        for d in ("src", "deps"):
            shutil.rmtree(out / d, ignore_errors=True)
    samples = {}
    for i, (dist, pkg) in P2_DISTS.items():
        d = P2_DIR / f"sample{i}"
        module_file = next(p for p in sorted(d.glob("*.py")) if not p.name.startswith("test_"))
        samples[i] = {"dist": dist, "pkg": pkg, "file": module_file, "module": module_file.stem,
                      "key": without_imports(module_file.read_text())}
    manifest = {"created": now_iso(), "cutoff": CUTOFF, "exclude_newer": EXCLUDE_NEWER, "dists": {}, "programs": {}}
    for dist in sorted({s["dist"] for s in samples.values()}):
        mine = {i: s for i, s in samples.items() if s["dist"] == dist}
        pkg = next(iter(mine.values()))["pkg"]
        rels = pypi_releases(dist)
        with cf.ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda r: fetch(r["url"], out / "archives" / r["filename"], r["sha256"]), rels))
        matches = {}
        for r in rels:
            files = package_files(archive_files(out / "archives" / r["filename"]), pkg)
            for i, s in mine.items():
                hits = [p for p, data in files.items() if p.split("/")[-1] == s["file"].name
                        and without_imports(data.decode("utf-8", "replace")) == s["key"]]
                if hits:
                    matches.setdefault(i, {})[r["version"]] = hits[0]
        missing = sorted(set(mine) - set(matches))
        if missing:
            sys.exit(f"{dist}: no release matches sample(s) {missing}")
        common = [r for r in rels if all(r["version"] in matches[i] for i in mine)]
        if not common:
            sys.exit(f"{dist}: no single release matches all its samples: {matches}")
        rel = common[-1]  # the files are identical in every candidate; the newest one is taken
        files = package_files(archive_files(out / "archives" / rel["filename"]), pkg)
        layout = Layout(files, pkg)
        src = out / "src" / f"{dist}-{rel['version']}"
        rewrites = {}
        if not src.exists():
            tmp = src.with_name(src.name + ".tmp")
            shutil.rmtree(tmp, ignore_errors=True)
            for p, data in files.items():
                dest = tmp / (layout.new_path(p) if p.endswith(".py") else p)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if p.endswith(".py"):
                    text, log = rewrite_imports(data.decode("utf-8"), p, layout)
                    rewrites[p] = log
                    dest.write_text(text)
                else:
                    dest.write_bytes(data)
            atomic_write_json(tmp / "_rewrites.json", rewrites)
            tmp.replace(src)
        manifest["dists"][dist] = {
            "package": pkg, "version": rel["version"], "date": rel["date"], "file": rel["filename"], "sha256": rel["sha256"],
            "candidates": [r["version"] for r in common], "renamed": layout.renamed, "flat_subpackages": layout.flat_dirs,
            "src": str(src.relative_to(DATASETS)), "module_paths": {f"sample{i}": matches[i][rel["version"]] for i in mine}}
    # one deps directory for all projects: the releases themselves (for imports the authors left package-absolute,
    # e.g. pymonet's `from pymonet.maybe import Maybe`) and their dependencies
    reqs = [f"{d}=={v['version']}" for d, v in manifest["dists"].items()] + P2_EXTRAS
    if not (out / "deps").exists():
        tmp = out / "deps.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        uv_install(tmp, reqs)
        tmp.replace(out / "deps")
    manifest["deps"] = {"dir": "p2/deps", "requirements": reqs,
                        "installed": sorted(p.name for p in (out / "deps").glob("*.dist-info"))}
    install_hook()
    manifest["hook"] = "phase1_paths.pth in the site-packages of .venv and .venv-pynguin"
    for i, s in sorted(samples.items()):
        d = manifest["dists"][s["dist"]]
        entry = {"module": s["module"], "source": str(s["file"].relative_to(REPO)), "dist": s["dist"],
                 "version": d["version"], "category": structural_category(s["file"].read_text()),
                 "site_dirs": ["p2/deps"], "path_append": [d["src"]] + [f"{d['src']}/{f}" for f in d["flat_subpackages"]]}
        if f"sample{i}" in P2_NOTES:
            entry["note"] = P2_NOTES[f"sample{i}"]
        entry["import_check"] = import_check(s["file"], s["module"], runtime_env(entry))
        manifest["programs"][f"sample{i}"] = entry
        print(f"sample{i:<3} {s['module']:18} {s['dist']}=={d['version']:10} {entry['category']:15} {entry['import_check']}", flush=True)
    atomic_write_json(out / "manifest.json", manifest)
    ok = sum(all(v == "ok" for v in e["import_check"].values()) for e in manifest["programs"].values())
    print(f"{ok}/{len(samples)} modules import in both venvs -> {out / 'manifest.json'}")


# ----------------------------------------------------------------------------- p1

P1_DIR = REPO / "100_300 LOC p1"
P1_CATS = {"cat1": "cat1_scripts", "cat2": "cat2_functions", "cat3": "cat3_classes"}
# third-party packages the p1 modules (and the project files they import) need; one shared directory
P1_DEPS = ["numpy", "matplotlib", "scipy", "cvxpy", "tqdm", "requests", "pymongo", "gevent", "pandas", "sqlalchemy",
           "discord.py", "youtube_dl", "anthropic", "opencv-python-headless", "scikit-video", "onnxruntime", "pillow",
           "plyfile", "pytz", "ipython", "tabulate", "gdown"]
# tried one by one, each may fail on a given machine (no index access, no C library to build against): reported
P1_OPTIONAL = [(["torch"], "https://download.pytorch.org/whl/cpu"), (["tensorflow-cpu"], None), (["insightface"], None),
               (["--no-deps", "opennsfw2"], None),  # facefusion; its own tensorflow requirement = tensorflow-cpu above
               (["mysqlclient"], None), (["pyaudio"], None)]
# why a module cannot be imported here, whatever error comes first (the authors' files are used as they are)
P1_NOTES = {
    "cat1_s15": "script: parses command-line arguments when imported; as for the 0-100 LOC scripts, Pynguin cannot test it",
    **{k: "hydra (2013) needs pymongo 2 (pymongo.errors.TimeoutError, removed in pymongo 3); none for Python 3.12"
       for k in ("cat2_s1", "cat3_s5", "cat3_s6")},
    "cat2_s2": "Python 2 code at module level (str.decode('hex'))",
    "cat2_s5": "needs torch (CPU build from download.pytorch.org): installed only if that index is reachable",
    "cat2_s6": "needs torch and gaussian-splatting's CUDA rasterizer (diff_gaussian_rasterization): GPU only",
    "cat2_s9": "Stoner (2023) imports numpy.NaN, removed in numpy 2 (the venvs have numpy 2)",
    **{k: "vbench is Python 2 code (exec statement, cPickle)" for k in ("cat2_s10", "cat3_s14")},
    "cat2_s11": "Windows only (win32api) and the PortAudio C library (pyaudio)",
    "cat2_s12": "MySQLdb (mysqlclient) needs the MySQL client C library to build (installed if the machine has it)",
    **{k: "relative import at module level (from .x import ...): it cannot be imported as a top-level module"
       for k in ("cat3_s8", "cat3_s12")},
    "cat3_s9": "runs a stock-market simulation that never ends when imported",
    **{k: "starts a Discord bot (network login) when imported" for k in ("cat3_s10", "cat3_s11")},
}
# data files a module reads when it is imported (copied next to it in every work directory)
P1_DATA = {"cat3_s9": ["Data/dowstocks.csv"]}
GH_URL = r"https://github\.com/([^/\s]+)/([^/\s]+)/blob/([^/\s]+)/(\S+)"


def git(repo, *args, check=True):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()[-500:]}")
    return p.stdout


def p1_samples():
    """{name: {category, file, origin}}: the source URL is the module's first-line comment or cat*/a.txt."""
    import re
    urls = {}
    for cat in ("cat2", "cat3"):
        for line in (P1_DIR / cat / "a.txt").read_text().splitlines():
            if " - " in line:
                n, u = line.split(" - ", 1)
                urls[f"{cat}/s{n.strip()}"] = u.split()[0]
    out = {}
    for f in sorted(P1_DIR.glob("cat*/s*/example.py")):
        cat, s = f.parent.parent.name, f.parent.name
        first = f.read_text(errors="replace").splitlines()[0]
        m = re.search(GH_URL, first) or re.search(GH_URL, urls.get(f"{cat}/{s}", ""))
        out[f"{cat}_{s}"] = {"category": P1_CATS[cat], "file": f,
                             "origin": dict(zip(("owner", "repo", "branch", "path"), m.groups())) if m else None}
    return out


def match_commit(repo, ref, path, key):
    """The repository as it was at CUTOFF if `path` there equals the authors' module apart from comments and
    imports (one consistent state for all files of the project); else the newest earlier commit where it does;
    else the most similar version (ratio < 1 recorded). Author dates: rebased histories keep them."""
    import difflib
    log = [ln.split() for ln in git(repo, "log", "--format=%H %as", ref).splitlines() if ln]
    base = next(((sha, d) for sha, d in log if d <= CUTOFF), None)
    if base:
        src = git(repo, "show", f"{base[0]}:{path}", check=False)
        if src and without_imports(src) == key:
            return {"commit": base[0], "date": base[1], "ratio": 1.0, "state": "repository at the cutoff date"}
    best = None
    for line in [ln for ln in git(repo, "log", "--format=%H %as", ref, "--", path).splitlines() if ln][:80]:
        sha, date = line.split()
        if date > CUTOFF:
            continue
        src = git(repo, "show", f"{sha}:{path}", check=False)
        k = without_imports(src) if src else None
        if k == key:
            return {"commit": sha, "date": date, "ratio": 1.0, "state": "last commit of the file before the cutoff"}
        r = difflib.SequenceMatcher(None, k or "", key or "").ratio()
        if best is None or r > best["ratio"]:
            best = {"commit": sha, "date": date, "ratio": round(r, 4), "state": "most similar version"}
    return best


def export_tree(repo, sha, dest):
    """The .py files of the repository at `sha` (sparse worktree: only those blobs are fetched)."""
    if dest.exists():
        return
    tmp = dest.with_name(dest.name + ".tmp")
    if tmp.exists():
        git(repo, "worktree", "remove", "--force", str(tmp), check=False)
        shutil.rmtree(tmp, ignore_errors=True)
    git(repo, "worktree", "add", "--no-checkout", "--detach", str(tmp), sha)
    git(tmp, "sparse-checkout", "set", "--no-cone", "*.py")
    git(tmp, "checkout", "--quiet")
    git(repo, "worktree", "move", str(tmp), str(dest))


def p1_overlay(name, samples, out):
    """The authors' own copies of the project's files, placed before the rebuilt project on the path: helper files
    they kept in a sample folder (cat3/s4 i3.py, cat3/s5 copy_state_db.py ...) and the modules of the other samples
    from the same directory of the same repository (hydra: copier.py is cat3/s5, oplog_applier.py is cat3/s6)."""
    o = samples[name]["origin"]
    files = {f.name: f for f in samples[name]["file"].parent.glob("*.py") if f.name != "example.py"}
    for other, s in samples.items():
        so = s["origin"]
        if other == name or not o or not so or (so["owner"], so["repo"]) != (o["owner"], o["repo"]) \
                or Path(so["path"]).parent != Path(o["path"]).parent:
            continue
        files.setdefault(Path(so["path"]).name, s["file"])
        files.update({f.name: f for f in s["file"].parent.glob("*.py") if f.name != "example.py"})
    files.pop(Path(o["path"]).name if o else "example.py", None)
    if not files:
        return None
    d = out / "overlay" / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    for fname, f in files.items():
        shutil.copy(f, d / fname)
    return str(d.relative_to(DATASETS))


def install_deps(target, reqs, optional):
    """Required packages (all or nothing), then each optional group on its own. Re-runs add what is missing."""
    uv_install(target, reqs)
    status = read_heavy(target)
    for group, index in optional:
        key = " ".join(group)
        if status.get(key) == "installed":
            continue
        cmd = ["uv", "pip", "install", "--python", str(VENV_PY), "--target", str(target), "--exclude-newer", EXCLUDE_NEWER,
               *(["--index", index, "--index-strategy", "unsafe-best-match"] if index else []), *group]
        p = subprocess.run(cmd, capture_output=True, text=True)
        status[key] = "installed" if p.returncode == 0 else ("skipped: " + (p.stderr.strip().splitlines() or ["?"])[-1])[:300]
    atomic_write_json(target / "_heavy.json", status)
    return status


def prepare_p1(force=False):
    out = DATASETS / "p1"
    if force:
        shutil.rmtree(out / "deps", ignore_errors=True)
    samples = p1_samples()
    manifest = {"created": now_iso(), "cutoff": CUTOFF, "exclude_newer": EXCLUDE_NEWER, "repos": {}, "programs": {}}
    for name, s in samples.items():
        o = s["origin"]
        entry = {"module": "example", "source": str(s["file"].relative_to(REPO)), "category": s["category"],
                 "structural_category": structural_category(s["file"].read_text()), "site_dirs": ["p1/deps"],
                 "path_append": [], "data_files": [], "origin": None}
        overlay = p1_overlay(name, samples, out)
        if o:
            slug = f"{o['owner']}__{o['repo']}"
            repo = out / "repos" / slug
            if not repo.exists():
                repo.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                                f"https://github.com/{o['owner']}/{o['repo']}.git", str(repo)], check=True)
            ref = f"origin/{o['branch']}" if git(repo, "rev-parse", "--verify", "--quiet", f"origin/{o['branch']}", check=False) else "HEAD"
            m = match_commit(repo, ref, o["path"], without_imports(s["file"].read_text()))
            if m:
                src = out / "src" / f"{slug}@{m['commit'][:12]}"
                export_tree(repo, m["commit"], src)
                rel = str(src.relative_to(DATASETS))
                here = str(Path(rel) / Path(o["path"]).parent)
                entry["path_append"] = list(dict.fromkeys([here, rel] + ([f"{rel}/src"] if (src / "src").is_dir() else [])))
                for df in P1_DATA.get(name, []):
                    dest = out / "data" / name / Path(df).name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(subprocess.run(["git", "-C", str(repo), "show", f"{m['commit']}:{df}"],
                                                    capture_output=True, check=True).stdout)
                    entry["data_files"].append(str(dest.relative_to(DATASETS)))
                manifest["repos"].setdefault(slug, {"url": f"https://github.com/{o['owner']}/{o['repo']}", "ref": ref, "exports": []})
                if rel not in manifest["repos"][slug]["exports"]:
                    manifest["repos"][slug]["exports"].append(rel)
            entry["origin"] = {**o, **(m or {"commit": None, "ratio": None})}
        if name in P1_NOTES:
            entry["note"] = P1_NOTES[name]
        if overlay:
            entry["path_append"].insert(0, overlay)
            entry["overlay"] = sorted(f.name for f in (DATASETS / overlay).iterdir())
        manifest["programs"][name] = entry
        print(f"{name:9} {(o or {}).get('repo', '-'):28} match={entry['origin'] and entry['origin']['ratio']} "
              f"{(entry['origin'] or {}).get('state', '')}", flush=True)
    (out / "deps").mkdir(parents=True, exist_ok=True)
    optional = install_deps(out / "deps", P1_DEPS, P1_OPTIONAL)
    manifest["deps"] = {"dir": "p1/deps", "requirements": P1_DEPS, "optional": optional,
                        "installed": sorted(p.name for p in (out / "deps").glob("*.dist-info"))}
    install_hook()
    manifest["hook"] = "phase1_paths.pth in the site-packages of .venv and .venv-pynguin"
    for name, entry in manifest["programs"].items():
        entry["import_check"] = import_check(REPO / entry["source"], "example", runtime_env(entry),
                                             [DATASETS / d for d in entry["data_files"]])
        print(f"{name:9} {entry['category']:15} {entry['import_check']}", flush=True)
    atomic_write_json(out / "manifest.json", manifest)
    ok = sum(all(v == "ok" for v in e["import_check"].values()) for e in manifest["programs"].values())
    print(f"{ok}/{len(samples)} modules import in both venvs -> {out / 'manifest.json'}")


def read_heavy(deps):
    try:
        return json.loads((deps / "_heavy.json").read_text())
    except (OSError, ValueError):
        return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("set", choices=("p2", "p1"))
    ap.add_argument("--force", action="store_true", help="rebuild the dependency directory (and p2's src/)")
    args = ap.parse_args()
    {"p2": prepare_p2, "p1": prepare_p1}[args.set](force=args.force)


if __name__ == "__main__":
    main()
