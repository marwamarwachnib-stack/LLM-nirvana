import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from cleanroom.static_analysis import analyse, line_counts
from cleanroom.stdlib310 import stdlib_310


def facts_for(src, local=None):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "m.py"
        p.write_text(textwrap.dedent(src), encoding="utf-8")
        return analyse(p, local)


class TestStdin(unittest.TestCase):
    def test_module_level_input(self):
        f = facts_for("x = input()\n")
        self.assertTrue(f.stdin_at_import)

    def test_sys_stdin_at_module_level(self):
        self.assertTrue(facts_for("import sys\ndata = sys.stdin.read()\n").stdin_at_import)

    def test_from_sys_import_stdin(self):
        self.assertTrue(facts_for("from sys import stdin\nfor l in stdin: pass\n").stdin_at_import)

    def test_main_guard_only(self):
        f = facts_for("""
            def f(): return 1
            if __name__ == "__main__":
                print(input())
        """)
        self.assertFalse(f.stdin_at_import)
        self.assertTrue(f.stdin_in_main_guard)

    def test_uncalled_top_level_function(self):
        f = facts_for("""
            import sys
            def read():
                return sys.stdin.fileno()
        """)
        self.assertFalse(f.stdin_at_import)
        self.assertTrue(f.stdin_in_functions)

    def test_called_through_helper(self):
        f = facts_for("""
            def a(): return input()
            def main(): return a()
            main()
        """)
        self.assertTrue(f.stdin_at_import)

    def test_method_body_not_executed(self):
        f = facts_for("""
            class C:
                def m(self): return input()
        """)
        self.assertFalse(f.stdin_at_import)

    def test_default_argument_is_executed(self):
        self.assertTrue(facts_for("def f(a=input()): return a\n").stdin_at_import)

    def test_embedded_data_named_input_is_not_stdin(self):
        f = facts_for('input = """1 2"""\nprint(input.split())\n')
        self.assertFalse(f.stdin_at_import)


class TestImports(unittest.TestCase):
    def test_classification(self):
        f = facts_for("""
            import os, collections.abc
            from . import sibling
            from ..pkg import thing
            import helper
            import requests
            try:
                import ujson
            except ImportError:
                ujson = None
            from typing import TYPE_CHECKING
            if TYPE_CHECKING:
                from attr import Attribute
            def f():
                import numpy
        """, local={"helper"})
        self.assertEqual(f.imports_stdlib, ["collections", "os", "typing"])
        self.assertEqual(f.imports_relative, [".", "..pkg"])
        self.assertEqual(f.imports_local, ["helper"])
        self.assertEqual(f.imports_unresolved, ["numpy", "requests"])
        self.assertEqual(f.imports_optional_unresolved, ["ujson"])
        self.assertEqual(f.imports_type_checking, ["attr"])

    def test_removed_stdlib_modules_count_as_stdlib_310(self):
        self.assertEqual(facts_for("import distutils.version\nimport imp\n").imports_stdlib,
                         ["distutils", "imp"])

    def test_stdlib_310_set(self):
        s = stdlib_310()
        self.assertNotIn("tomllib", s)
        for m in ("distutils", "imp", "asyncore", "telnetlib", "os", "typing"):
            self.assertIn(m, s)

    @unittest.skipUnless(sys.version_info >= (3, 11), "only meaningful on newer interpreters")
    def test_added_module_excluded(self):
        self.assertEqual(facts_for("import tomllib\n").imports_unresolved, ["tomllib"])


class TestShape(unittest.TestCase):
    def test_python2_source_does_not_parse(self):
        f = facts_for('print "hello"\n')
        self.assertFalse(f.parses)
        self.assertIn("SyntaxError", f.parse_error)

    def test_counts(self):
        f = facts_for("""
            def a(): pass
            async def b(): pass
            class C:
                def m(self): pass
                def n(self): pass
            X = 1
            if __name__ == "__main__":
                a()
        """)
        self.assertEqual((f.n_functions, f.n_classes, f.n_methods), (2, 1, 2))
        self.assertEqual(f.toplevel_statements, 1)

    def test_stub_detection(self):
        self.assertTrue(facts_for('def f(x):\n    """doc"""\n    pass\n').is_stub)
        self.assertTrue(facts_for("def f():\n    raise NotImplementedError('x')\n").is_stub)
        self.assertFalse(facts_for("def f():\n    return 1\n").is_stub)
        self.assertFalse(facts_for("x = 1\n").is_stub)

    def test_line_counts(self):
        text = '"""doc"""\n\n# comment\nx = 1  # trailing\ny = (1,\n     2)\n'
        self.assertEqual(line_counts(text), (6, 5, 4))


if __name__ == "__main__":
    unittest.main()
