"""Top-level standard-library module names of CPython 3.10.

The authors' saved reports record Python 3.10.12. The analysis may run on a
newer interpreter, so its `sys.stdlib_module_names` is corrected for modules
added after 3.10 and modules removed before the running version.
"""
from __future__ import annotations

import sys

ADDED_AFTER_310 = {
    (3, 11): {"tomllib"},
}

REMOVED_AFTER_310 = {
    (3, 12): {"asynchat", "asyncore", "distutils", "imp", "smtpd"},
    (3, 13): {"aifc", "audioop", "cgi", "cgitb", "chunk", "crypt", "imghdr",
              "lib2to3", "mailcap", "msilib", "nis", "nntplib", "ossaudiodev",
              "pipes", "sndhdr", "spwd", "sunau", "telnetlib", "uu", "xdrlib"},
}


def stdlib_310(version: tuple[int, int] = sys.version_info[:2]) -> frozenset[str]:
    if version < (3, 10):
        raise RuntimeError("sys.stdlib_module_names requires Python >= 3.10")
    names = set(sys.stdlib_module_names)
    for since, mods in ADDED_AFTER_310.items():
        if version >= since:
            names -= mods
    for since, mods in REMOVED_AFTER_310.items():
        if version >= since:
            names |= mods
    return frozenset(names)


STDLIB_310 = stdlib_310()
