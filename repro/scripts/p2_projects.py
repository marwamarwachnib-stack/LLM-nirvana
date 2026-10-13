"""Rebuild the project context of the 43 p2 modules (Lukasczyk et al. benchmark projects).

The repository holds only the authors' copy of each target module (imports flattened, e.g.
`from base import ValidationError`), and its coverage reports show the tests were run from inside the
package directory of each project. This script:
  1. maps every sample to its upstream project (from module names / imports / paths in the saved reports);
  2. downloads every PyPI release of that project published before 2024-01-27 (the repository's date)
     and picks the release whose files are most similar to the authors' copies;
  3. writes repro/data/p2_projects.json and unpacks the chosen package directories to
     /opt/repro/p2_projects/<project>/ (sandboxes copy the package contents next to the target module,
     reproducing the authors' "run from inside the package" layout).
The chosen releases are installed into the conda env `p2` by env/setup_p2_env.sh.
"""
from __future__ import annotations

import difflib
import io
import json
import re
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from common import P2, REPO, classify_structure, write_json

CACHE = Path("/opt/repro/pypi_cache")
DEST = Path("/opt/repro/p2_projects")
CUTOFF = "2024-01-27"

# sample -> (pypi project, path of the module inside the distribution, extra package subdirs to flatten)
SAMPLES = {
    "sample1": ("flutils", "flutils/decorators.py"), "sample2": ("flutils", "flutils/objutils.py"),
    "sample3": ("flutils", "flutils/packages.py"), "sample4": ("flutils", "flutils/strutils.py"),
    "sample5": ("flutils", "flutils/txtutils.py"), "sample6": ("flutils", "flutils/validators.py"),
    "sample7": ("codetiming", "codetiming/_timers.py"),
    "sample8": ("httpie", "httpie/compat.py"), "sample9": ("httpie", "httpie/config.py"),
    "sample10": ("httpie", "httpie/sessions.py"), "sample11": ("httpie", "httpie/ssl_.py"),
    "sample12": ("httpie", "httpie/uploads.py"),
    "sample13": ("pymonet", "pymonet/box.py"), "sample14": ("pymonet", "pymonet/either.py"),
    "sample15": ("pymonet", "pymonet/immutable_list.py"), "sample16": ("pymonet", "pymonet/lazy.py"),
    "sample17": ("pymonet", "pymonet/maybe.py"), "sample18": ("pymonet", "pymonet/monad_try.py"),
    "sample19": ("pymonet", "pymonet/semigroups.py"), "sample20": ("pymonet", "pymonet/validation.py"),
    "sample21": ("pymonet", "pymonet/utils.py"),
    "sample22": ("python-string-utils", "string_utils/generation.py"),
    "sample23": ("python-string-utils", "string_utils/manipulation.py"),
    "sample24": ("sty", "sty/register.py"),
    "sample25": ("typesystem", "typesystem/base.py"), "sample26": ("typesystem", "typesystem/formats.py"),
    "sample27": ("typesystem", "typesystem/json_schema.py"), "sample28": ("typesystem", "typesystem/schemas.py"),
    "sample29": ("typesystem", "typesystem/forms.py"),
    "sample30": ("typesystem", "typesystem/tokenize/tokenize_yaml.py"),
    "sample31": ("typesystem", "typesystem/tokenize/tokens.py"),
    "sample32": ("typesystem", "typesystem/fields.py"),
    "sample33": ("docstring-parser", "docstring_parser/common.py"),
    "sample34": ("docstring-parser", "docstring_parser/google.py"),
    "sample35": ("docstring-parser", "docstring_parser/numpydoc.py"),
    "sample36": ("docstring-parser", "docstring_parser/rest.py"),
    "sample37": ("dataclasses-json", "dataclasses_json/api.py"),
    "sample38": ("dataclasses-json", "dataclasses_json/core.py"),
    "sample39": ("dataclasses-json", "dataclasses_json/undefined.py"),
    "sample40": ("pdir2", "pdir/api.py"), "sample41": ("pdir2", "pdir/attr_category.py"),
    "sample42": ("flutes", "flutes/exception.py"), "sample43": ("flutes", "flutes/run.py"),
}
IMPORT = re.compile(r"^\s*(from\s+\S+\s+import|import\s)")


def normalize(src: str) -> list[str]:
    """Drop import lines, comments-only lines and blank lines so flattened imports do not count as differences."""
    out = []
    for line in src.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or IMPORT.match(line):
            continue
        out.append(s)
    return out


def releases(project: str) -> list[tuple[str, dict]]:
    d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{project}/json"))
    out = []
    for ver, files in d["releases"].items():
        files = [f for f in files if f["upload_time"][:10] <= CUTOFF and not f.get("yanked")]
        if not files:
            continue
        sdist = [f for f in files if f["packagetype"] == "sdist"]
        whl = [f for f in files if f["filename"].endswith("-none-any.whl")]
        f = (whl or sdist)[0]
        out.append((ver, f))
    return out


def read_dist(f: dict) -> dict[str, str]:
    """Return {path inside package: text} for a wheel or sdist (sdist paths have the top folder stripped)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    local = CACHE / f["filename"]
    if not local.exists():
        local.write_bytes(urllib.request.urlopen(f["url"]).read())
    files = {}
    data = local.read_bytes()
    if f["filename"].endswith(".whl") or f["filename"].endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n in z.namelist():
                if n.endswith(".py"):
                    key = n if f["filename"].endswith(".whl") else n.split("/", 1)[-1]
                    files[key] = z.read(n).decode("utf-8", "replace")
    else:
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            for m in t.getmembers():
                if m.name.endswith(".py") and m.isfile():
                    files[m.name.split("/", 1)[-1]] = t.extractfile(m).read().decode("utf-8", "replace")
    return files


def main() -> None:
    by_project: dict[str, list[str]] = {}
    for sid, (proj, _) in SAMPLES.items():
        by_project.setdefault(proj, []).append(sid)
    result = {"cutoff": CUTOFF, "projects": {}, "samples": {}}
    for proj, sids in by_project.items():
        scores = []
        for ver, f in releases(proj):
            try:
                files = read_dist(f)
            except Exception as e:  # noqa: BLE001
                print("skip", proj, ver, e)
                continue
            per = {}
            for sid in sids:
                path = SAMPLES[sid][1]
                ours = [p for p in (P2 / "pynguin coverage" / sid).glob("*.py") if not p.name.startswith("test_")][0]
                theirs = files.get(path)
                per[sid] = round(difflib.SequenceMatcher(None, normalize(ours.read_text()), normalize(theirs)).ratio(), 4) if theirs else 0.0
            scores.append((sum(per.values()) / len(per), ver, f["filename"], per))
        scores.sort(key=lambda x: (x[0], x[1]))
        best = scores[-1]
        result["projects"][proj] = {"chosen_version": best[1], "file": best[2], "mean_similarity": round(best[0], 4),
                                    "candidates": [(v, round(s, 4)) for s, v, _, _ in scores]}
        print(f"{proj}: best {best[1]} similarity {best[0]:.4f} ({len(scores)} releases compared)", flush=True)
        files = read_dist({"filename": best[2], "url": ""}) if (CACHE / best[2]).exists() else {}
        pkg_root = SAMPLES[sids[0]][1].split("/")[0]
        out = DEST / proj
        if out.exists():
            shutil.rmtree(out)
        for p, text in files.items():
            if p.startswith(pkg_root + "/"):
                q = out / p
                q.parent.mkdir(parents=True, exist_ok=True)
                q.write_text(text)
        for sid in sids:
            path = SAMPLES[sid][1]
            src = [p for p in (P2 / "pynguin coverage" / sid).glob("*.py") if not p.name.startswith("test_")][0]
            pkg_dirs = [str(Path(proj) / Path(path).parent)]
            if Path(path).parent != Path(pkg_root):
                pkg_dirs.append(str(Path(proj) / pkg_root))   # e.g. typesystem/tokenize + typesystem
            result["samples"][sid] = {
                "project": proj, "version": best[1], "upstream_path": path, "module_file": src.name,
                "similarity_to_upstream": best[3][sid], "package_dirs": pkg_dirs,
                "structure_rule": classify_structure(src.read_text()),
            }
    write_json(REPO / "repro" / "data" / "p2_projects.json", result)


if __name__ == "__main__":
    main()
