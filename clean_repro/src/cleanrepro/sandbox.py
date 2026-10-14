"""Sandboxes: fresh copies of a program under test plus a test suite, under $CR_HOME/work.

Original files are only ever read (copied).  Each sandbox directory is recreated from scratch.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .paths import REPO, WORK


def fresh(*parts: str) -> Path:
    d = WORK.joinpath(*parts)
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def copy_in(src: Path, sandbox: Path, name: str | None = None) -> Path:
    src = Path(src)
    if not src.is_absolute():
        src = REPO / src
    dst = sandbox / (name or src.name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return dst


def small_program(row: dict, *parts: str) -> Path:
    """Sandbox with the small-set program as example.py (the name used by the authors' prompts
    and by the saved Pynguin suites)."""
    sb = fresh(*parts)
    copy_in(row["module_path"], sb, "example.py")
    return sb


def small_developer(row: dict, *parts: str) -> Path:
    """Sandbox for the Exercism developer tests: they import the program under the exercise's
    module name (e.g. affine_cipher), whose original file is only a stub; the reference solution
    example.py is copied under that name.  Helper files next to the tests are copied as well."""
    sb = fresh(*parts)
    prog = (REPO / row["module_path"]).parent
    copy_in(row["module_path"], sb, row["developer_module_name"] + ".py")
    copy_in(row["developer_suite"], sb)
    for helper in prog.glob("*.py"):
        if helper.name not in ("example.py", "test_example.py", Path(row["developer_suite"]).name,
                               row["developer_module_name"] + ".py") and not helper.name.startswith("get_"):
            copy_in(helper, sb)
    return sb
