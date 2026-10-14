from cleanrepro.p2_context import flatten_for_sandbox, normalise


def test_relative_and_absolute_self_imports():
    src = ("from .compat import is_windows\nfrom typesystem.base import Message\nimport typesystem.fields\n"
           "from . import __version__\nfrom . import fields\nimport os\nfrom requests import get\n")
    out = flatten_for_sandbox(src, "typesystem", {"fields.py", "compat.py", "base.py"}, {})
    assert out.splitlines() == ["from compat import is_windows", "from base import Message", "import fields",
                                "from __init__ import __version__", "import fields", "import os",
                                "from requests import get"]


def test_subpackage_resolution_and_renames():
    src = "from .constants import X\nfrom ..compat import Y\nfrom .types import PathType\n"
    out = flatten_for_sandbox(src, "httpie", {"compat.py"}, {}, here="cli")
    assert out.splitlines()[:2] == ["from cli.constants import X", "from compat import Y"]
    out2 = flatten_for_sandbox("from .types import PathType\n", "flutes", {"types_renamed.py"}, {"types": "types_renamed"})
    assert out2.strip() == "from types_renamed import PathType"


def test_normalise_ignores_comments_and_relative_dots():
    assert normalise("from .a import b  # c\n\n# x\n") == normalise("from a import b\n")
