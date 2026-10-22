"""Provenance checks: is a benchmark module a (flattened) copy of a file in a released artifact?

Normalization N (applied identically to both texts before comparison):
  N1  Every import statement (located with `ast`, whole multi-line span, including a trailing
      comment on its last line) is replaced by a canonical line that keeps the imported names,
      their order and `as` aliases, but reduces the module path to its last component after
      removing relative-import dots and the project's package prefix. `from <pkg> import x`,
      `from . import x` and `from __init__ import x` all become `import x`.
      Documented module renames (e.g. flutes `types_renamed` -> `types`) are applied here.
  N2  Comment-only lines of the exact form `# from <dotted.name or .>` are dropped (markers the
      authors left where they flattened imports).
  Every other line must be byte-identical. Line endings are not normalized.

Raw SHA-256 of both texts and of both canonical texts are recorded, together with the list of
import statements that differ before normalization.
"""
from __future__ import annotations

import ast
import hashlib
import io
import re
import tarfile
import warnings
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

MARKER = re.compile(rb"^[ \t]*# from [\w.]*[ \t]*\r?\n?$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- archives (never extracted to disk)

def archive_members(path: Path) -> dict[str, bytes]:
    """Regular `.py` members of a wheel/zip or sdist tarball, read in memory."""
    out: dict[str, bytes] = {}
    name = path.name
    if name.endswith((".whl", ".zip", ".egg")):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.filename.endswith(".py") and not info.is_dir():
                    out[info.filename] = z.read(info)
    elif name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar")):
        with tarfile.open(path) as t:
            for m in t.getmembers():
                if m.isfile() and m.name.endswith(".py"):
                    f = t.extractfile(m)
                    if f is not None:
                        out[m.name] = f.read()
    else:
        raise ValueError(f"unsupported archive: {name}")
    return out


def package_files(members: dict[str, bytes], package: str) -> dict[str, bytes]:
    """Members inside the package directory, keyed by path relative to the package's parent
    (e.g. 'typesystem/tokenize/tokens.py'), for the shallowest occurrence of the package."""
    roots = sorted({k[: k.index(f"{package}/")] for k in members if f"{package}/" in k
                    and (k.startswith(f"{package}/") or f"/{package}/" in k)}, key=len)
    for root in roots:
        sel = {k[len(root):]: v for k, v in members.items()
               if k.startswith(root + f"{package}/")}
        if f"{package}/__init__.py" in sel:
            return sel
    return {}


# ---------------------------------------------------------------- normalization

def _last(module: str) -> str:
    return module.rsplit(".", 1)[-1] if module else ""


def _canon_module(module: str | None, level: int, package: str, renames: dict[str, str]) -> str:
    mod = module or ""
    if level == 0:
        if mod == package or mod == "__init__":
            mod = ""
        elif mod.startswith(package + "."):
            mod = mod[len(package) + 1:]
    mod = _last(mod)
    return renames.get(mod, mod)


def canonical_import(node: ast.stmt, package: str, renames: dict[str, str]) -> str:
    if isinstance(node, ast.Import):
        parts = []
        for a in node.names:
            name = renames.get(_last(a.name), _last(a.name)) if a.name.startswith(package + ".") \
                or a.name in renames else a.name
            parts.append(name + (f" as {a.asname}" if a.asname else ""))
        return "import " + ", ".join(parts)
    assert isinstance(node, ast.ImportFrom)
    mod = _canon_module(node.module, node.level, package, renames)
    names = ", ".join(a.name + (f" as {a.asname}" if a.asname else "") for a in node.names)
    return f"import {names}" if mod == "" else f"from {mod} import {names}"


def import_spans(text: str) -> list[tuple[int, int, int, ast.stmt]]:
    """(first line, last line, column, node) of every import statement, 1-based lines."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        tree = ast.parse(text)
    return sorted((n.lineno, n.end_lineno, n.col_offset, n) for n in ast.walk(tree)
                  if isinstance(n, (ast.Import, ast.ImportFrom)))


def canonicalize(data: bytes, package: str, renames: dict[str, str] | None = None) -> bytes:
    renames = renames or {}
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    spans = import_spans(text)
    starts: dict[int, list] = {}
    for first, last, col, node in spans:
        starts.setdefault(first, []).append((last, col, node))
    out: list[bytes] = []
    i = 1
    while i <= len(lines):
        if i in starts:
            group = starts[i]
            last = max(g[0] for g in group)
            indent = lines[i - 1][: group[0][1]]
            canon = "; ".join(canonical_import(g[2], package, renames) for g in group)
            out.append(f"{indent}{canon}\n".encode())
            i = last + 1
            continue
        raw = lines[i - 1].encode("utf-8")
        if not MARKER.match(raw):
            out.append(raw)
        i += 1
    return b"".join(out)


@dataclass
class Comparison:
    raw_equal: bool
    canonical_equal: bool
    benchmark_sha256: str
    release_sha256: str
    benchmark_canonical_sha256: str
    release_canonical_sha256: str
    changed_imports: list[tuple[str, str]] = field(default_factory=list)


def _import_lines(data: bytes) -> list[str]:
    text = data.decode("utf-8")
    lines = text.splitlines()
    return [" ".join(l.strip() for l in lines[a - 1:b]) for a, b, _, _ in import_spans(text)]


def compare(benchmark: bytes, release: bytes, package: str,
            renames: dict[str, str] | None = None) -> Comparison:
    cb = canonicalize(benchmark, package, renames)
    cr = canonicalize(release, package, renames)
    changed: list[tuple[str, str]] = []
    if benchmark != release and cb == cr:
        changed = [(r, b) for r, b in zip(_import_lines(release), _import_lines(benchmark)) if r != b]
    return Comparison(benchmark == release, cb == cr, sha256(benchmark), sha256(release),
                      sha256(cb), sha256(cr), changed)


# ---------------------------------------------------------------- derivation of flat siblings

def flatten_imports(data: bytes, package: str, flat_names: dict[str, str] | None = None
                    ) -> tuple[bytes, list[tuple[str, str]]]:
    """Derivation F: rewrite project-internal imports into the flat form the authors used
    (evidence: every flattened benchmark module of the same projects), keeping line numbers.
    Relative imports and `from <package>[.x] import ...` become `from <last> import ...`
    (`import ...` when the module is the package itself). `import <package>.x` statements and
    all other imports are untouched. `flat_names` maps real -> flat module names."""
    flat_names = flat_names or {}
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    edits = []
    for first, last, col, node in import_spans(text):
        if not isinstance(node, ast.ImportFrom):
            continue
        mod = node.module or ""
        if node.level > 0:
            flat = _last(mod)
        elif mod == package:
            flat = ""
        elif mod.startswith(package + "."):
            flat = _last(mod)
        else:
            continue
        flat = flat_names.get(flat, flat)
        names = ", ".join((flat_names.get(a.name, a.name) if not flat else a.name)
                          + (f" as {a.asname}" if a.asname else "") for a in node.names)
        new = f"import {names}" if not flat else f"from {flat} import {names}"
        edits.append((first, last, col, new))
    changes = []
    for first, last, col, new in sorted(edits, reverse=True):
        old = "".join(lines[first - 1:last])
        indent = lines[first - 1][:col]
        lines[first - 1:last] = [f"{indent}{new}\n"] + ["\n"] * (last - first)
        changes.append((" ".join(l.strip() for l in old.splitlines()), new))
    return "".join(lines).encode("utf-8"), sorted(changes)


def flatten_relative_imports(data: bytes, flat_names: dict[str, str] | None = None
                             ) -> tuple[bytes, list[tuple[str, str]]]:
    """Rewrite relative imports into flat top-level imports, keeping line numbers:
    `from .x import y` -> `from x import y`; `from . import y` -> `import y`;
    `from ..a.b import y` -> `from b import y`. Absolute imports are untouched.
    `flat_names` maps a module's real name to its flat name (e.g. flutes 'types' ->
    'types_renamed', as the authors renamed it). Returns new bytes and (old, new) pairs."""
    flat_names = flat_names or {}
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    edits = []
    for first, last, col, node in import_spans(text):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            mod = _last(node.module or "")
            mod = flat_names.get(mod, mod)
            names = ", ".join((flat_names.get(a.name, a.name) if not mod else a.name)
                              + (f" as {a.asname}" if a.asname else "") for a in node.names)
            new = f"import {names}" if not mod else f"from {mod} import {names}"
            edits.append((first, last, col, new))
    changes = []
    for first, last, col, new in sorted(edits, reverse=True):
        old = "".join(lines[first - 1:last])
        indent = lines[first - 1][:col]
        repl = [f"{indent}{new}\n"] + ["\n"] * (last - first)
        lines[first - 1:last] = repl
        changes.append((" ".join(l.strip() for l in old.splitlines()), new))
    return "".join(lines).encode("utf-8"), sorted(changes)
