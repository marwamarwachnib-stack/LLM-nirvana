"""Every .pyc in the authors' folders, against the source it was compiled from (re-audit, decision 19).

A CPython 3.10 .pyc header holds the source's size and modification time; its code object can be compared with
a fresh compile of the source we have. p2's ChatGPT folders keep only the .pyc of the module ChatGPT's tests ran
against: its candidate source is the module of the same sample in 'pynguin coverage'. Tests compiled by pytest
(assertion rewriting) are compared by size only. Run with the authors' Python (.venv-run, 3.10):

    .venv-run/bin/python -I audit/pyc_forensics.py
Writes audit/pyc_forensics.csv. Reads the repository only.
"""
import csv
import datetime as dt
import glob
import marshal
import os
import struct
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def comparable(co):
    """A code object without its file name, recursively (line numbers kept)."""
    consts = tuple(comparable(c) if isinstance(c, types.CodeType) else c for c in co.co_consts)
    return co.co_code, consts, co.co_names, co.co_varnames, co.co_name, co.co_firstlineno, co.co_linetable


def candidate(pyc):
    folder = os.path.dirname(os.path.dirname(pyc))
    stem = os.path.basename(pyc).split(".")[0]
    if os.path.exists(os.path.join(folder, stem + ".py")):
        return os.path.join(folder, stem + ".py")
    if "/ChatGPT coverage/" in pyc and stem == "example":
        mods = [p for p in glob.glob(os.path.join(REPO, "100_300 LOC p2", "pynguin coverage", os.path.basename(folder), "*.py"))
                if not os.path.basename(p).startswith("test_")]
        return mods[0] if len(mods) == 1 else None
    return None


def main():
    rows = []
    for pyc in sorted(glob.glob(os.path.join(REPO, "*LOC*", "**", "*.pyc"), recursive=True)):
        with open(pyc, "rb") as f:
            head = f.read(16)
            co = marshal.load(f)
        mtime, size = struct.unpack("<II", head[8:16])
        src = candidate(pyc)
        if src is None:
            verdict = "no candidate source"
        elif "pytest" in os.path.basename(pyc):
            verdict = "test: size " + ("equal" if os.path.getsize(src) == size else "different")
        else:
            try:
                same = comparable(compile(open(src, "rb").read(), src, "exec")) == comparable(co)
                verdict = "module: bytecode " + ("identical" if same else "different")
            except SyntaxError as e:
                verdict = f"module: source does not compile ({e.msg})"
        rows.append({"pyc": os.path.relpath(pyc, REPO), "recorded_source": co.co_filename,
                     "source_mtime_utc": dt.datetime.fromtimestamp(mtime, dt.timezone.utc).isoformat(timespec="seconds"),
                     "recorded_source_size": size, "candidate_source": src and os.path.relpath(src, REPO),
                     "candidate_size": src and os.path.getsize(src), "verdict": verdict})
    with open(os.path.join(HERE, "pyc_forensics.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(len(rows), "pyc files:", counts)
    for area in ("0_100 LOC", "100_300 LOC p2"):
        ts = sorted(r["source_mtime_utc"] for r in rows if r["pyc"].startswith(area))
        print(f"{area}: source modification times {ts[0]} .. {ts[-1]}")


if __name__ == "__main__":
    main()
