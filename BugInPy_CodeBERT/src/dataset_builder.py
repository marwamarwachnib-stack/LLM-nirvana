"""STEPS 3-4 - Build a function-level buggy/fixed dataset from BugsInPy.

For every bug instance:

1. Resolve ``buggy_commit_id`` / ``fixed_commit_id`` in the upstream repository
   and record their history relationship (direct parent? number of commits).
2. Take the non-test Python files listed in ``bug_patch.txt`` and read both
   versions straight from git (``git show <sha>:<path>``) - nothing is checked out.
3. Verify that the official patch is consistent with the two file versions
   (removed lines exist in the buggy file, added lines exist in the fixed file).
4. Parse both versions with :mod:`ast`, enumerate *outermost* function
   definitions (module functions and class methods; nested functions stay inside
   their parent) and map the patch's changed lines onto them.
5. For every function touched by the patch that exists in both versions and whose
   code differs after normalisation (comments/docstrings/formatting removed):
       buggy version  -> label 1
       fixed version  -> label 0   (paired negative, same ``pair_id``)
   Everything else is *not* a sample but is recorded in ``function_diagnostics.csv``
   with the reason (added-only, deleted-only, cosmetic-only change, parse error...).

Unchanged functions are never used as negatives (they are not verified as correct).

Outputs (``data/processed``): ``samples.csv``, ``samples.jsonl``,
``function_diagnostics.csv``, ``bug_diagnostics.csv``, ``dataset_stats.json``.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import textwrap
import tokenize
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset_exploration import TEST_PATH_RE, parse_kv, read_text  # noqa: E402

warnings.filterwarnings("ignore", category=SyntaxWarning)
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


# ============================================================== git helpers
def git(repo: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()[:300]}")
    return r.stdout


def resolve(repo: Path, sha: str) -> str | None:
    try:
        return git(repo, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}").strip() or None
    except RuntimeError:
        return None


def file_at(repo: Path, sha: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{path}"], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", errors="replace")


# ============================================================ patch parsing
@dataclass
class FilePatch:
    old_path: str
    new_path: str
    removed: dict[int, str] = field(default_factory=dict)   # buggy line no -> text
    added: dict[int, str] = field(default_factory=dict)     # fixed line no -> text
    context_old: dict[int, str] = field(default_factory=dict)


def parse_patch_lines(text: str) -> list[FilePatch]:
    out: list[FilePatch] = []
    cur, o, n = None, 0, 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" ")
            cur = FilePatch(parts[2][2:], parts[3][2:])
            out.append(cur)
            continue
        if cur is None or line.startswith(("---", "+++", "index ", "new file", "deleted file",
                                           "similarity", "rename ", "old mode", "new mode")):
            continue
        m = HUNK_RE.match(line)
        if m:
            o, n = int(m.group(1)), int(m.group(3))
            continue
        if line.startswith("-"):
            cur.removed[o] = line[1:]; o += 1
        elif line.startswith("+"):
            cur.added[n] = line[1:]; n += 1
        elif line.startswith(" ") or line == "":
            cur.context_old[o] = line[1:]; o += 1; n += 1
        # "\ No newline at end of file" and others: ignore
    return out


# ======================================================= function extraction
@dataclass
class Func:
    qualname: str
    start: int          # first line incl. decorators (1-based)
    end: int
    source: str


def extract_functions(src: str) -> list[Func]:
    """Outermost functions (module level + methods of (nested) classes)."""
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    funcs: list[Func] = []
    seen: Counter = Counter()

    def visit(node: ast.AST, prefix: str) -> None:
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = min([d.lineno for d in ch.decorator_list] + [ch.lineno])
                q = f"{prefix}{ch.name}"
                seen[q] += 1
                if seen[q] > 1:                  # e.g. property getter/setter, conditional defs
                    q = f"{q}#{seen[q]}"
                funcs.append(Func(q, start, ch.end_lineno, "".join(lines[start - 1:ch.end_lineno])))
            elif isinstance(ch, ast.ClassDef):
                visit(ch, f"{prefix}{ch.name}.")
            elif isinstance(ch, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
                visit(ch, prefix)                # defs under `if PY3:` / `try:` at module/class level

    visit(tree, "")
    return funcs


def strip_comments(code: str) -> str:
    """Remove ``#`` comments with the tokenizer (string contents are untouched)."""
    try:
        toks = [t for t in tokenize.generate_tokens(io.StringIO(code).readline)
                if t.type != tokenize.COMMENT]
        return tokenize.untokenize(toks)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return code


def canonical(code: str) -> str | None:
    """Formatting/comment/docstring-insensitive representation used for change detection & dedup."""
    try:
        tree = ast.parse(textwrap.dedent(code))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            b = node.body
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) \
                    and isinstance(b[0].value.value, str):
                node.body = b[1:] or [ast.Pass()]
    return ast.unparse(tree)


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def owner(funcs: list[Func], line: int) -> Func | None:
    for f in funcs:
        if f.start <= line <= f.end:
            return f
    return None


# ================================================================= per bug
def process_bug(bug_dir: Path, project: str, repo: Path) -> tuple[dict, list[dict], list[dict]]:
    bug_id = bug_dir.name
    uid = f"{project}-{bug_id}"
    info = parse_kv(read_text(bug_dir / "bug.info")[0])
    diag = {"uid": uid, "project": project, "bug_id": bug_id,
            "buggy_commit_id": info.get("buggy_commit_id"), "fixed_commit_id": info.get("fixed_commit_id")}
    samples, fdiag = [], []

    buggy = resolve(repo, info.get("buggy_commit_id", ""))
    fixed = resolve(repo, info.get("fixed_commit_id", ""))
    diag.update(buggy_sha=buggy, fixed_sha=fixed)
    if not buggy or not fixed:
        diag["status"] = "commit_not_found"
        return diag, samples, fdiag
    parents = git(repo, "rev-list", "--parents", "-n", "1", fixed).split()[1:]
    diag["buggy_is_parent_of_fixed"] = buggy in parents
    diag["fixed_has_multiple_parents"] = len(parents) > 1
    diag["commits_between"] = int(git(repo, "rev-list", "--count", f"{buggy}..{fixed}").strip() or 0)
    diag["buggy_is_ancestor"] = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", buggy, fixed]).returncode == 0

    patch_text = read_text(bug_dir / "bug_patch.txt")[0]
    fps = [fp for fp in parse_patch_lines(patch_text)
           if fp.new_path.endswith(".py") and not TEST_PATH_RE.search(fp.new_path)]
    diag["src_files_in_patch"] = len(fps)
    if not fps:
        diag["status"] = "no_python_source_change"
        return diag, samples, fdiag

    n_lines_ok = n_lines_total = 0
    reasons = Counter()
    for fp in fps:
        bsrc, fsrc = file_at(repo, buggy, fp.old_path), file_at(repo, fixed, fp.new_path)
        if bsrc is None or fsrc is None:
            reasons["file_missing_in_commit"] += 1
            continue
        bl, fl = bsrc.splitlines(), fsrc.splitlines()
        f_ok = f_tot = 0
        for ln, t in list(fp.removed.items()) + list(fp.context_old.items()):
            f_tot += 1; f_ok += 0 < ln <= len(bl) and bl[ln - 1] == t
        for ln, t in fp.added.items():
            f_tot += 1; f_ok += 0 < ln <= len(fl) and fl[ln - 1] == t
        n_lines_ok += f_ok; n_lines_total += f_tot
        if f_ok != f_tot:
            # the official patch does not describe these two file versions -> the functions it
            # touches cannot be identified reliably: exclude the file (conservative)
            reasons["patch_inconsistent_file"] += 1
            fdiag.append({"uid": uid, "file": fp.new_path, "qualname": None,
                          "status": "patch_inconsistent_file", "detail": f"{f_ok}/{f_tot} lines match"})
            continue
        try:
            bfuncs, ffuncs = extract_functions(bsrc), extract_functions(fsrc)
        except SyntaxError as e:
            reasons["file_parse_error"] += 1
            fdiag.append({"uid": uid, "file": fp.new_path, "qualname": None, "status": "file_parse_error",
                          "detail": str(e)[:200]})
            continue

        touched: set[str] = set()
        outside = 0
        for ln in fp.removed:
            f = owner(bfuncs, ln); touched.add(f.qualname) if f else None; outside += f is None
        for ln in fp.added:
            f = owner(ffuncs, ln); touched.add(f.qualname) if f else None; outside += f is None
        if outside:
            reasons["changed_lines_outside_functions"] += 1
        bmap, fmap = {f.qualname: f for f in bfuncs}, {f.qualname: f for f in ffuncs}

        for q in sorted(touched):
            rec = {"uid": uid, "file": fp.new_path, "qualname": q}
            if q not in bmap:
                fdiag.append({**rec, "status": "added_in_fix"}); continue
            if q not in fmap:
                fdiag.append({**rec, "status": "deleted_in_fix"}); continue
            b, f = bmap[q], fmap[q]
            cb, cf = canonical(b.source), canonical(f.source)
            if cb is None or cf is None:
                fdiag.append({**rec, "status": "function_parse_error"}); continue
            if cb == cf:
                fdiag.append({**rec, "status": "cosmetic_change_only"}); continue
            fdiag.append({**rec, "status": "paired"})
            pair_id = f"{uid}::{fp.new_path}::{q}"
            for label, fn, sha, path, can in ((1, b, buggy, fp.old_path, cb), (0, f, fixed, fp.new_path, cf)):
                code = textwrap.dedent(fn.source).rstrip() + "\n"
                samples.append({
                    "sample_id": f"{pair_id}::{'buggy' if label else 'fixed'}",
                    "pair_id": pair_id, "uid": uid, "project": project, "bug_id": bug_id,
                    "version": "buggy" if label else "fixed", "label": label,
                    "commit": sha, "file": path, "qualname": q,
                    "start_line": fn.start, "end_line": fn.end, "n_lines": fn.end - fn.start + 1,
                    "code": code, "code_no_comments": strip_comments(code),
                    "canonical_hash": sha1(can),
                })
    diag["patch_line_consistency"] = round(n_lines_ok / n_lines_total, 4) if n_lines_total else None
    diag["n_pairs"] = len(samples) // 2
    diag["n_functions_touched"] = sum(1 for d in fdiag if d["uid"] == uid and d.get("qualname"))
    diag["issues"] = ";".join(f"{k}={v}" for k, v in sorted(reasons.items()))
    diag["status"] = "ok" if samples else "no_valid_pair"
    return diag, samples, fdiag


# ============================================================ dedup / stats
def deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Remove exact (canonical) duplicates and label conflicts, keeping pairs intact."""
    rep = {"samples_before": int(len(df))}
    # 1) label conflicts: identical canonical code labelled 1 in one bug and 0 in another.
    #    Observed in BugsInPy: the *fixed* version of bug A is the *buggy* version of a later bug B
    #    in the same function. B's failing test proves that code is buggy, so the label-0 sample is
    #    contradicted -> drop the pair that owns the contradicted negative; keep B's pair.
    lab = df.groupby("canonical_hash")["label"].nunique()
    conflict = set(lab[lab > 1].index)
    bad_pairs = set(df.loc[df["canonical_hash"].isin(conflict) & (df["label"] == 0), "pair_id"])
    rep["label_conflict_hashes"] = len(conflict)
    rep["pairs_dropped_label_conflict"] = len(bad_pairs)
    rep["label_conflict_examples"] = sorted(bad_pairs)
    df = df[~df["pair_id"].isin(bad_pairs)]
    # 2) exact duplicates with the same label: keep the first pair, drop later pairs entirely
    dup_mask = df.duplicated(["canonical_hash", "label"], keep="first")
    dup_pairs = set(df.loc[dup_mask, "pair_id"])
    rep["duplicate_pairs_dropped"] = sorted(dup_pairs)
    rep["pairs_dropped_duplicate"] = len(dup_pairs)
    df = df[~df["pair_id"].isin(dup_pairs)].reset_index(drop=True)
    rep["samples_after"] = int(len(df))
    return df, rep


def build_stats(df: pd.DataFrame, bugs: pd.DataFrame, fdiag: pd.DataFrame, dedup: dict) -> dict:
    return {
        "n_projects_in_benchmark": int(bugs["project"].nunique()),
        "n_bugs_in_benchmark": int(len(bugs)),
        "bug_status": bugs["status"].value_counts().to_dict(),
        "buggy_is_parent_of_fixed": bugs["buggy_is_parent_of_fixed"].value_counts(dropna=False).to_dict(),
        "buggy_is_ancestor_of_fixed": bugs["buggy_is_ancestor"].value_counts(dropna=False).to_dict(),
        "commits_between_buggy_and_fixed": bugs["commits_between"].describe().round(2).to_dict(),
        "patch_line_consistency_mean": float(bugs["patch_line_consistency"].mean()),
        "bugs_with_patch_fully_consistent": int((bugs["patch_line_consistency"] == 1).sum()),
        "function_status": fdiag["status"].value_counts().to_dict(),
        "dedup": dedup,
        "final": {
            "n_projects": int(df["project"].nunique()),
            "n_bugs": int(df["uid"].nunique()),
            "n_pairs": int(df["pair_id"].nunique()),
            "n_buggy_samples": int((df["label"] == 1).sum()),
            "n_clean_samples": int((df["label"] == 0).sum()),
            "class_distribution": df["label"].value_counts(normalize=True).round(4).to_dict(),
            "pairs_per_bug": df.groupby("uid")["pair_id"].nunique().describe().round(2).to_dict(),
            "bugs_single_pair": int((df.groupby("uid")["pair_id"].nunique() == 1).sum()),
            "samples_per_project": df["project"].value_counts().to_dict(),
            "code_lines": df["n_lines"].describe().round(2).to_dict(),
            "code_chars": df["code"].str.len().describe().round(2).to_dict(),
            "missing_code": int(df["code"].isna().sum() + (df["code"].str.strip() == "").sum()),
            "exact_duplicate_code_rows": int(df.duplicated("code").sum()),
            "canonical_duplicate_rows": int(df.duplicated("canonical_hash").sum()),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bugsinpy", default="data/raw/BugsInPy")
    ap.add_argument("--upstream", default="data/raw/upstream")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--projects", nargs="*", help="restrict to these projects")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    jobs = []
    for pdir in sorted((Path(a.bugsinpy) / "projects").iterdir()):
        if not pdir.is_dir() or (a.projects and pdir.name not in a.projects):
            continue
        url = parse_kv(read_text(pdir / "project.info")[0])["github_url"].rstrip("/")
        repo = Path(a.upstream) / f"{url.rsplit('/', 1)[1]}.git"
        for b in (pdir / "bugs").iterdir():
            if b.is_dir():
                jobs.append((b, pdir.name, repo))

    def run(job):
        try:
            return process_bug(*job)
        except Exception as e:  # recorded, never silently dropped
            return {"uid": f"{job[1]}-{job[0].name}", "project": job[1], "bug_id": job[0].name,
                    "status": f"error: {e}"[:300]}, [], []

    with ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(run, jobs))

    bugs = pd.DataFrame([r[0] for r in results])
    raw = pd.DataFrame([s for r in results for s in r[1]])
    fdiag = pd.DataFrame([d for r in results for d in r[2]])
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    bugs.sort_values(["project", "bug_id"], key=lambda s: s.map(lambda v: int(v) if str(v).isdigit() else v)) \
        .to_csv(out / "bug_diagnostics.csv", index=False)
    fdiag.to_csv(out / "function_diagnostics.csv", index=False)
    df, dedup = deduplicate(raw.sort_values("sample_id").reset_index(drop=True))
    df.to_csv(out / "samples.csv", index=False)
    df.to_json(out / "samples.jsonl", orient="records", lines=True, force_ascii=False)
    stats = build_stats(df, bugs, fdiag, dedup)
    (out / "dataset_stats.json").write_text(json.dumps(stats, indent=2, default=str))
    print(json.dumps(stats["final"], indent=2, default=str))


if __name__ == "__main__":
    main()
