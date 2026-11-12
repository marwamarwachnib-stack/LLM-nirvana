"""STEP 2 - Exploration of the BugsInPy benchmark (metadata only).

Reads every ``projects/<project>/bugs/<id>/`` folder of a local BugsInPy clone,
parses the metadata files *without assuming* a fixed schema, analyses each
``bug_patch.txt`` diff and writes:

* ``results/exploration/bugs_metadata.csv`` / ``.jsonl`` - one row per bug
* ``results/exploration/patch_files.csv``                - one row per changed file
* ``results/exploration/exploration_summary.json``        - aggregate statistics
* ``results/exploration/dataset_exploration_report.md``   - human-readable report

Nothing is downloaded and nothing in the raw dataset is modified.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

KV_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?(.*?)"?\s*$')
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
TEST_PATH_RE = re.compile(r"(^|/)(tests?|testing)(/|$)|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")


# --------------------------------------------------------------------------- io
def read_text(path: Path) -> tuple[str, str]:
    """Read a text file, detecting UTF-16 (BOM) files present in BugsInPy."""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = KV_RE.match(line.replace("\r", ""))
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


# ------------------------------------------------------------------------ diffs
def parse_patch(text: str) -> list[dict]:
    """Split a unified git diff into per-file records with hunk statistics."""
    files: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" ")
            cur = {"old_path": parts[2][2:] if len(parts) > 2 else None,
                   "new_path": parts[3][2:] if len(parts) > 3 else None,
                   "hunks": 0, "added": 0, "removed": 0,
                   "new_file": False, "deleted_file": False,
                   "hunk_contexts": []}
            files.append(cur)
        elif cur is None:
            continue
        elif line.startswith("new file mode"):
            cur["new_file"] = True
        elif line.startswith("deleted file mode"):
            cur["deleted_file"] = True
        elif line.startswith("@@"):
            cur["hunks"] += 1
            m = HUNK_RE.match(line)
            if m and m.group(5).strip():
                cur["hunk_contexts"].append(m.group(5).strip())
        elif line.startswith("+") and not line.startswith("+++"):
            cur["added"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            cur["removed"] += 1
    for f in files:
        path = f["new_path"] or f["old_path"] or ""
        f["is_python"] = path.endswith(".py")
        f["is_test"] = bool(TEST_PATH_RE.search(path))
    return files


# ------------------------------------------------------------------------- main
def explore(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    projects_dir = root / "projects"
    bug_rows, file_rows = [], []
    anomalies: list[str] = []
    abbreviated: dict[str, list[str]] = defaultdict(list)
    projects_info = {}

    for proj_dir in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        project = proj_dir.name
        pinfo_path = proj_dir / "project.info"
        pinfo = parse_kv(read_text(pinfo_path)[0]) if pinfo_path.exists() else {}
        projects_info[project] = {
            "github_url": pinfo.get("github_url"),
            "status": pinfo.get("status"),
            "extra_files": sorted(f.name for f in proj_dir.iterdir() if f.is_file() and f.name != "project.info"),
        }
        bugs_dir = proj_dir / "bugs"
        for entry in sorted(bugs_dir.iterdir(), key=lambda p: (not p.name.isdigit(), int(p.name) if p.name.isdigit() else 0, p.name)):
            if not entry.is_dir():
                anomalies.append(f"{project}: non-directory entry in bugs/: {entry.name!r}")
                continue
            files_present = sorted(f.name for f in entry.iterdir())
            row = {"project": project, "bug_id": entry.name,
                   "uid": f"{project}-{entry.name}", "files_present": ";".join(files_present)}

            info_path = entry / "bug.info"
            info = parse_kv(read_text(info_path)[0]) if info_path.exists() else {}
            if not info_path.exists():
                anomalies.append(f"{row['uid']}: missing bug.info")
            row.update({
                "buggy_commit_id": info.get("buggy_commit_id"),
                "fixed_commit_id": info.get("fixed_commit_id"),
                "python_version": info.get("python_version"),
                "pythonpath": info.get("pythonpath"),
                "test_file": info.get("test_file"),
                "bug_info_keys": ";".join(sorted(info)),
            })
            for k in ("buggy_commit_id", "fixed_commit_id"):
                v = row[k]
                if not v or not re.fullmatch(r"[0-9a-f]{7,40}", v):
                    anomalies.append(f"{row['uid']}: {k} is not a valid git SHA: {v!r}")
                elif len(v) < 40:
                    abbreviated[k].append(row["uid"])
            row["n_test_files_declared"] = len([t for t in (row["test_file"] or "").split(";") if t.strip()])

            rt = entry / "run_test.sh"
            if rt.exists():
                cmds = [l for l in read_text(rt)[0].splitlines() if l.strip()]
                row["n_test_commands"] = len(cmds)
                row["test_runner"] = ("pytest" if any("pytest" in c for c in cmds)
                                      else "unittest" if any("unittest" in c for c in cmds)
                                      else "other")
            else:
                row["n_test_commands"], row["test_runner"] = 0, None

            req = entry / "requirements.txt"
            row["requirements_encoding"] = read_text(req)[1] if req.exists() else None

            patch_path = entry / "bug_patch.txt"
            if patch_path.exists():
                ptext = read_text(patch_path)[0]
                pfiles = parse_patch(ptext)
            else:
                pfiles = []
                anomalies.append(f"{row['uid']}: missing bug_patch.txt")
            if patch_path.exists() and not pfiles:
                anomalies.append(f"{row['uid']}: bug_patch.txt contains no file diffs")
            src = [f for f in pfiles if f["is_python"] and not f["is_test"]]
            row.update({
                "patch_files": len(pfiles),
                "patch_py_src_files": len(src),
                "patch_test_files": sum(f["is_test"] for f in pfiles),
                "patch_non_py_files": sum(not f["is_python"] for f in pfiles),
                "patch_hunks": sum(f["hunks"] for f in pfiles),
                "patch_src_hunks": sum(f["hunks"] for f in src),
                "patch_added": sum(f["added"] for f in pfiles),
                "patch_removed": sum(f["removed"] for f in pfiles),
                "patch_src_changed_lines": sum(f["added"] + f["removed"] for f in src),
                "patch_new_or_deleted_files": sum(f["new_file"] or f["deleted_file"] for f in pfiles),
                "hunk_context_functions": ";".join(sorted({c for f in src for c in f["hunk_contexts"]})),
            })
            bug_rows.append(row)
            for f in pfiles:
                file_rows.append({"uid": row["uid"], "project": project, "bug_id": entry.name,
                                  "path": f["new_path"] or f["old_path"],
                                  **{k: f[k] for k in ("is_python", "is_test", "hunks", "added",
                                                       "removed", "new_file", "deleted_file")},
                                  "hunk_contexts": " | ".join(f["hunk_contexts"])})

    bugs = pd.DataFrame(bug_rows)
    files = pd.DataFrame(file_rows)

    # duplicated commit pairs (same fix registered twice)
    dup_pairs = bugs[bugs.duplicated(["project", "buggy_commit_id", "fixed_commit_id"], keep=False)]
    for _, g in dup_pairs.groupby(["project", "buggy_commit_id", "fixed_commit_id"]):
        anomalies.append("duplicate commit pair: " + ", ".join(g["uid"]))

    for k, uids in abbreviated.items():
        anomalies.append(f"{len(uids)} bugs use an abbreviated {k} (resolvable in upstream repo): "
                         f"projects={sorted({u.rsplit('-', 1)[0] for u in uids})}")

    try:
        rev = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%H %ci"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # pragma: no cover
        rev = "unknown"

    per_project = bugs.groupby("project").agg(
        bugs=("uid", "count"),
        src_py_files_changed_mean=("patch_py_src_files", "mean"),
        src_changed_lines_median=("patch_src_changed_lines", "median"),
        bugs_single_src_hunk=("patch_src_hunks", lambda s: int((s == 1).sum())),
        bugs_no_src_change=("patch_py_src_files", lambda s: int((s == 0).sum())),
    ).reset_index()
    per_project["github_url"] = per_project["project"].map(lambda p: projects_info[p]["github_url"])

    summary = {
        "dataset": "BugsInPy", "dataset_revision": rev, "root": str(root.as_posix()),
        "n_projects": int(bugs["project"].nunique()), "n_bugs": int(len(bugs)),
        "bugs_per_project": bugs["project"].value_counts().sort_index().to_dict(),
        "bug_info_key_variants": dict(Counter(bugs["bug_info_keys"])),
        "missing_python_version": int(bugs["python_version"].isna().sum()),
        "python_versions": dict(Counter(bugs["python_version"].fillna("MISSING"))),
        "test_runners": dict(Counter(bugs["test_runner"].fillna("MISSING"))),
        "requirements_encodings": dict(Counter(bugs["requirements_encoding"].fillna("MISSING"))),
        "patch_files_total": int(len(files)),
        "patch": {
            "bugs_touching_only_1_src_file": int((bugs["patch_py_src_files"] == 1).sum()),
            "bugs_touching_multiple_src_files": int((bugs["patch_py_src_files"] > 1).sum()),
            "bugs_with_no_python_src_change": int((bugs["patch_py_src_files"] == 0).sum()),
            "bugs_whose_patch_also_edits_tests": int((bugs["patch_test_files"] > 0).sum()),
            "bugs_whose_patch_edits_non_py_files": int((bugs["patch_non_py_files"] > 0).sum()),
            "src_changed_lines": bugs["patch_src_changed_lines"].describe().round(2).to_dict(),
            "src_hunks": bugs["patch_src_hunks"].describe().round(2).to_dict(),
        },
        "per_project": per_project.to_dict(orient="records"),
        "projects_info": projects_info,
        "anomalies": anomalies,
    }
    return bugs, files, summary


def write_report(summary: dict, bugs: pd.DataFrame, out: Path) -> None:
    p = summary["patch"]
    pp = pd.DataFrame(summary["per_project"])
    lines = [
        "# BugsInPy - Dataset Exploration Report", "",
        f"- Dataset root: `{summary['root']}`",
        f"- Dataset revision (git): `{summary['dataset_revision']}`",
        f"- Projects: **{summary['n_projects']}**  |  Bug instances: **{summary['n_bugs']}**",
        f"- Changed files across all patches: {summary['patch_files_total']}", "",
        "## 1. Physical structure (as observed)", "",
        "```", "BugsInPy/", "  framework/bin/bugsinpy-{checkout,compile,test,coverage,...}",
        "  projects/<project>/project.info          # github_url, status",
        "  projects/<project>/bugs/<id>/bug.info     # buggy/fixed commit, test_file, ...",
        "  projects/<project>/bugs/<id>/bug_patch.txt# unified diff buggy -> fixed",
        "  projects/<project>/bugs/<id>/run_test.sh  # bug-revealing test command(s)",
        "  projects/<project>/bugs/<id>/requirements.txt, setup.sh (optional)", "```", "",
        "**The benchmark contains no source code.** Buggy and fixed program versions must be "
        "obtained by checking out `buggy_commit_id` / `fixed_commit_id` of each project's upstream repository.", "",
        "## 2. Projects", "",
        pp[["project", "bugs", "github_url", "src_py_files_changed_mean", "src_changed_lines_median",
            "bugs_single_src_hunk", "bugs_no_src_change"]].round(2).to_markdown(index=False), "",
        "## 3. Bug metadata", "",
        f"- `bug.info` key variants: `{summary['bug_info_key_variants']}`",
        f"- Missing `python_version`: {summary['missing_python_version']} bugs",
        f"- Test runners in `run_test.sh`: {summary['test_runners']}",
        f"- `requirements.txt` encodings: {summary['requirements_encodings']}",
        f"- Declared test files per bug: min {bugs['n_test_files_declared'].min()}, "
        f"max {bugs['n_test_files_declared'].max()}, mean {bugs['n_test_files_declared'].mean():.2f}", "",
        "## 4. Bug-fix patches", "",
        f"- Bugs whose fix touches exactly 1 non-test Python file: {p['bugs_touching_only_1_src_file']}",
        f"- Bugs whose fix touches >1 non-test Python files: {p['bugs_touching_multiple_src_files']}",
        f"- Bugs whose patch has **no** non-test Python change: {p['bugs_with_no_python_src_change']}",
        f"- Patches that also edit test files: {p['bugs_whose_patch_also_edits_tests']}",
        f"- Patches that edit non-Python files: {p['bugs_whose_patch_edits_non_py_files']}",
        f"- Changed source lines per bug (+/-): {p['src_changed_lines']}",
        f"- Source hunks per bug: {p['src_hunks']}", "",
        "## 5. How buggy/fixed versions are defined (from `framework/bin/bugsinpy-checkout`)", "",
        "- Fixed version = `git reset --hard <fixed_commit_id>` of the upstream repository.",
        "- Buggy version = `git reset --hard <buggy_commit_id>`; the bug-revealing `test_file`(s) "
        "of the fixed version are then copied into the buggy checkout.",
        "- `bug_patch.txt` is the source-code diff buggy -> fixed and identifies the code touched by the fix.",
        "- Large whole-file patches (see outliers below) suggest the buggy commit is not always the direct "
        "parent of the fix, so a patch may contain changes unrelated to the bug. To be verified against "
        "upstream history before building labels.", "",
        "Largest source patches (changed lines):", "",
        bugs.nlargest(5, "patch_src_changed_lines")[["uid", "patch_py_src_files", "patch_src_hunks",
                                                      "patch_src_changed_lines"]].to_markdown(index=False), "",
        f"Share of bugs with <= 20 changed source lines: {(bugs['patch_src_changed_lines'] <= 20).mean():.1%}", "",
        "## 6. Anomalies detected", "",
        *([f"- {a}" for a in summary["anomalies"]] or ["- none"]), "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="data/raw/BugsInPy")
    ap.add_argument("--out", default="results/exploration")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    bugs, files, summary = explore(Path(a.root))
    bugs.to_csv(out / "bugs_metadata.csv", index=False)
    bugs.to_json(out / "bugs_metadata.jsonl", orient="records", lines=True)
    files.to_csv(out / "patch_files.csv", index=False)
    (out / "exploration_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    write_report(summary, bugs, out / "dataset_exploration_report.md")
    print(f"{summary['n_projects']} projects, {summary['n_bugs']} bugs -> {out}")


if __name__ == "__main__":
    main()
