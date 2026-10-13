"""Build the per-sample sandbox templates for p2 from the evidence in the saved coverage reports.

The saved reports (statement_coverage*.txt) list every non-test file that sat next to the target
module when the authors ran the tests, e.g. sample30: base.py composites.py ... tokenize_yaml.py tokens.py.
For each sample this script copies exactly those files from the matched upstream release
(data/p2_projects.json), flattening their relative imports the same way the authors flattened the
target modules (`from .base import X` -> `from base import X`). Renamed files are resolved through
the `_renamed` suffix visible in the reports (flutes: types_renamed.py <- flutes/types.py).

Files listed with an absolute project path (httpie, pdir2) belonged to the authors' full project
checkout, i.e. the installed package in our env `p2`; only the local (relative) files are copied.
Output: /opt/repro/p2_sandboxes/<sample>/ and the field "sandbox_files" in data/p2_projects.json.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from common import P2, REPO

PROJ = Path("/opt/repro/p2_projects")
OUT = Path("/opt/repro/p2_sandboxes")
DATA = REPO / "repro" / "data" / "p2_projects.json"

REL_FROM = re.compile(r"^(\s*)from\s+(\.+)([\w.]*)\s+import\s+(.+)$")


def flatten_relative(src: str, renames: dict[str, str]) -> tuple[str, int]:
    """`from .x import y` -> `from x import y`; `from . import a` -> `import a`; renamed modules follow
    the authors' renaming (e.g. `from .types import PathType` -> `from types_renamed import PathType`)."""
    n = 0
    out = []
    for line in src.split("\n"):
        m = REL_FROM.match(line)
        if m:
            indent, dots, mod, names = m.groups()
            n += 1
            if mod:
                mod = renames.get(mod, mod)
                line = f"{indent}from {mod} import {names}"
            else:  # from . import a, b
                line = f"{indent}import {names}"
        out.append(line)
    return "\n".join(out), n


def listed_files(sid: str) -> tuple[list[str], list[str]]:
    rel, absolute = set(), set()
    for folder in (P2 / "pynguin coverage" / sid, P2 / "ChatGPT coverage" / sid):
        for rep in folder.glob("statement_coverage*.txt"):
            for line in rep.read_text().splitlines():
                parts = line.split()
                if not parts or parts[0] in ("Name", "TOTAL") or parts[0].startswith("-"):
                    continue
                name = parts[0]
                if Path(name).name.startswith("test_"):
                    continue
                (absolute if name.startswith("/") else rel).add(name)
    return sorted(rel), sorted(absolute)


def main() -> None:
    data = json.loads(DATA.read_text())
    for sid, info in data["samples"].items():
        rel, absolute = listed_files(sid)
        pkg_root = PROJ / info["project"] / info["upstream_path"].split("/")[0]
        index: dict[str, Path] = {}
        for p in sorted(pkg_root.rglob("*.py"), key=lambda p: len(p.parts)):  # shallowest wins
            index.setdefault(p.name, p)
        dst = OUT / sid
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        files, missing = [], []
        renames = {n[:-len("_renamed.py")]: n[:-3] for n in rel if n.endswith("_renamed.py")}
        pkg_name = pkg_root.name
        # absolute entries (authors' full checkout, e.g. .../pdir2-0.3.2/pdir/color.py) -> path inside the package
        for a in absolute:
            parts = Path(a).parts
            if pkg_name in parts:
                inner = Path(*parts[parts.index(pkg_name) + 1:])
                if inner.name != info["module_file"] or len(inner.parts) > 1:
                    rel.append(str(inner))
        for name in sorted(set(rel)):
            if name == info["module_file"]:
                continue  # the authors' target copy is added by the pipeline
            up = pkg_root / name if "/" in name else (index.get(name) or index.get(name.replace("_renamed", "")))
            if name == "__init__.py":
                if absolute:
                    # reports with absolute checkout paths list a local __init__.py with 0 statements:
                    # an empty file created by the authors, not the package's __init__.
                    (dst / name).write_text("")
                    files.append({"name": name, "upstream": None, "note": "empty (0 statements in saved reports)"})
                    continue
                up = pkg_root / "__init__.py"
            if Path(name).stem in sys.stdlib_module_names and "/" not in name:
                # e.g. flutes/types.py; the authors renamed it (types_renamed.py) because it shadows the stdlib
                missing.append(f"{name} (shadows stdlib, skipped)")
                continue
            if not up or not up.exists():
                missing.append(name)
                continue
            text, n = flatten_relative(up.read_text(), renames)
            (dst / name).parent.mkdir(parents=True, exist_ok=True)
            (dst / name).write_text(text)
            files.append({"name": name, "upstream": str(up.relative_to(PROJ)), "relative_imports_flattened": n})
        info["sandbox_files"] = files
        info["sandbox_missing"] = missing
        info["absolute_paths_in_reports"] = len(absolute)
        info["sandbox_dir"] = sid
        print(sid, [f["name"] for f in files], "missing:", missing, "abs:", len(absolute))
    DATA.write_text(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
