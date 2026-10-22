import io
import tarfile
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

from cleanroom import provenance as pv

UPSTREAM = textwrap.dedent('''\
    """Module doc."""
    import re
    from typesystem.base import Message, ValidationError
    from .fields import (
        Array,
        Field,
    )
    from . import formats
    from typesystem import unique


    def f(x):
        from typesystem.tokens import Token
        return re.sub("a", "b", x)
''').encode()

FLATTENED = textwrap.dedent('''\
    """Module doc."""
    import re
    from base import Message, ValidationError
    from fields import (
        Array,
        Field,
    )
    # from .
    import formats
    # from typesystem
    import unique


    def f(x):
        from tokens import Token
        return re.sub("a", "b", x)
''').encode()


class TestNormalization(unittest.TestCase):
    def test_flattened_copy_matches(self):
        c = pv.compare(FLATTENED, UPSTREAM, "typesystem")
        self.assertFalse(c.raw_equal)
        self.assertTrue(c.canonical_equal)
        self.assertEqual(c.benchmark_sha256, pv.sha256(FLATTENED))
        self.assertEqual(c.release_sha256, pv.sha256(UPSTREAM))
        self.assertIn(("from typesystem.base import Message, ValidationError",
                       "from base import Message, ValidationError"), c.changed_imports)

    def test_identical_is_raw_equal(self):
        c = pv.compare(UPSTREAM, UPSTREAM, "typesystem")
        self.assertTrue(c.raw_equal and c.canonical_equal)
        self.assertEqual(c.changed_imports, [])

    def test_non_import_change_is_detected(self):
        changed = FLATTENED.replace(b'"b"', b'"c"')
        self.assertFalse(pv.compare(changed, UPSTREAM, "typesystem").canonical_equal)

    def test_comment_change_is_detected(self):
        a = b"# see https://github.com/httpie/httpie/pull/1\nx = 1\n"
        b = b"# see https://github.com/httpie/cli/pull/1\nx = 1\n"
        self.assertFalse(pv.compare(a, b, "httpie").canonical_equal)

    def test_imported_names_must_match(self):
        changed = FLATTENED.replace(b"Message, ValidationError", b"Message")
        self.assertFalse(pv.compare(changed, UPSTREAM, "typesystem").canonical_equal)

    def test_alias_must_match(self):
        a = b"from .x import y as z\n"
        self.assertTrue(pv.compare(b"from x import y as z\n", a, "pkg").canonical_equal)
        self.assertFalse(pv.compare(b"from x import y as w\n", a, "pkg").canonical_equal)

    def test_unrelated_absolute_imports_compare_by_names(self):
        self.assertTrue(pv.compare(b"from os.path import join\n", b"from os.path import join\n", "pkg").canonical_equal)
        self.assertFalse(pv.compare(b"from os.path import join\n", b"from os.path import split\n", "pkg").canonical_equal)

    def test_init_and_package_imports_equivalent(self):
        self.assertTrue(pv.compare(b"from __init__ import __version__ #.\n",
                                   b"from . import __version__\n", "httpie").canonical_equal)

    def test_module_renames(self):
        self.assertTrue(pv.compare(b"from types_renamed import PathType\n", b"from .types import PathType\n",
                                   "flutes", {"types_renamed": "types"}).canonical_equal)
        self.assertFalse(pv.compare(b"from types_renamed import PathType\n", b"from .types import PathType\n",
                                    "flutes").canonical_equal)

    def test_marker_lines_only_of_exact_form(self):
        self.assertTrue(pv.MARKER.match(b"# from typesystem \n"))
        self.assertTrue(pv.MARKER.match(b"    # from . \n"))
        self.assertIsNone(pv.MARKER.match(b"# from here we start\n"))


class TestDerivation(unittest.TestCase):
    def test_flatten_imports(self):
        out, changes = pv.flatten_imports(UPSTREAM, "typesystem")
        text = out.decode()
        self.assertIn("from base import Message, ValidationError\n", text)
        self.assertIn("from fields import Array, Field\n", text)
        self.assertIn("import formats\n", text)
        self.assertIn("import unique\n", text)
        self.assertIn("    from tokens import Token\n", text)  # indentation kept
        self.assertEqual(len(text.splitlines()), len(UPSTREAM.decode().splitlines()))  # line numbers kept
        self.assertEqual(len(changes), 5)
        # every line outside an import statement is unchanged and keeps its line number
        spans = {i for a, b, _, _ in pv.import_spans(UPSTREAM.decode()) for i in range(a, b + 1)}
        up, down = UPSTREAM.decode().splitlines(), text.splitlines()
        for i, line in enumerate(up, 1):
            if i not in spans:
                self.assertEqual(down[i - 1], line)

    def test_flatten_keeps_other_imports(self):
        src = b"import json\nfrom collections import OrderedDict\nimport typesystem.x\n"
        out, changes = pv.flatten_imports(src, "typesystem")
        self.assertEqual(out, src)
        self.assertEqual(changes, [])

    def test_flatten_with_flat_names(self):
        out, _ = pv.flatten_imports(b"from .types import PathType\nfrom . import types\n", "flutes",
                                    {"types": "types_renamed"})
        self.assertEqual(out, b"from types_renamed import PathType\nimport types_renamed\n")

    def test_flatten_relative_only(self):
        out, _ = pv.flatten_relative_imports(b"from .a import b\nfrom pkg.c import d\n")
        self.assertEqual(out, b"from a import b\nfrom pkg.c import d\n")


class TestArchives(unittest.TestCase):
    def test_zip_and_tar_members_and_package_root(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            whl = d / "pkg-1.0-py3-none-any.whl"
            with zipfile.ZipFile(whl, "w") as z:
                z.writestr("pkg/__init__.py", "")
                z.writestr("pkg/a.py", "x = 1\n")
                z.writestr("pkg-1.0.dist-info/METADATA", "Name: pkg\n")
            tgz = d / "pkg-1.0.tar.gz"
            with tarfile.open(tgz, "w:gz") as t:
                for name, data in [("pkg-1.0/pkg/__init__.py", b""), ("pkg-1.0/pkg/a.py", b"x = 1\n"),
                                   ("pkg-1.0/tests/pkg/a.py", b"other\n"), ("pkg-1.0/setup.py", b"")]:
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    t.addfile(info, io.BytesIO(data))
            self.assertEqual(set(pv.archive_members(whl)), {"pkg/__init__.py", "pkg/a.py"})
            self.assertEqual(pv.package_files(pv.archive_members(whl), "pkg"),
                             {"pkg/__init__.py": b"", "pkg/a.py": b"x = 1\n"})
            self.assertEqual(pv.package_files(pv.archive_members(tgz), "pkg"),
                             {"pkg/__init__.py": b"", "pkg/a.py": b"x = 1\n"})
            with self.assertRaises(ValueError):
                pv.archive_members(d / "x.rpm")


if __name__ == "__main__":
    unittest.main()
