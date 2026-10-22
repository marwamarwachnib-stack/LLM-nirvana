import tempfile
import unittest
from pathlib import Path

from cleanroom import a6_audit, paths


class TestParsing(unittest.TestCase):
    def test_parse_missing(self):
        self.assertEqual(a6_audit.parse_missing("18, 29, 48-51"), {18, 29, 48, 49, 50, 51})
        self.assertEqual(a6_audit.parse_missing(""), set())
        self.assertEqual(a6_audit.parse_missing("12->15, 20"), {20})  # branch arcs ignored

    def test_coverage_row_statement_and_branch_reports(self):
        with tempfile.TemporaryDirectory() as d:
            s = Path(d) / "s.txt"
            s.write_text("Name   Stmts   Miss  Cover   Missing\n---\nforms.py  65  17  74%   49-54, 92\n")
            b = Path(d) / "b.txt"
            b.write_text("Name   Stmts   Miss Branch BrPart  Cover   Missing\nforms.py  65  17  14  5  72%   49-54\n")
            rs, rb = a6_audit.coverage_row(s, "forms.py"), a6_audit.coverage_row(b, "forms.py")
        self.assertEqual((rs["stmts"], rs["cover"], rs["missing_lines"]), (65, "74%", [49, 50, 51, 52, 53, 54, 92]))
        self.assertEqual((rb["cover"], rb["missing_lines"]), ("72%", [49, 50, 51, 52, 53, 54]))

    def test_statement_lines_excludes_docstrings_and_pragma_handlers(self):
        src = ('"""doc"""\ntry:\n    import yaml\nexcept ImportError:  # pragma: no cover\n    yaml = None\n'
               'def f():\n    """doc"""\n    assert yaml is not None\n    return 1\n')
        self.assertEqual(a6_audit.statement_lines(src), {2, 3, 6, 8, 9})


@unittest.skipUnless((paths.REPO_ROOT / "100_300 LOC p2").is_dir(), "snapshot not present")
class TestRealEvidence(unittest.TestCase):
    """The verified facts reported in A6 must hold on the snapshot."""

    @classmethod
    def setUpClass(cls):
        cls.audit = a6_audit.dependency_audit()

    def test_authors_runs_executed_dependency_gated_code(self):
        s30 = self.audit["p2/sample30"]["authors_coverage"]
        self.assertEqual(s30["pynguin_statement"]["row"]["cover"], "100%")
        self.assertEqual(s30["pynguin_statement"]["row"]["gated_missed"]["requires the yaml module"], [])
        self.assertGreater(len(s30["chatgpt_statement"]["row"]["gated_executed"]["requires the yaml module"]), 0)
        s29 = self.audit["p2/sample29"]["authors_coverage"]
        for k in ("pynguin_statement", "chatgpt_statement"):
            self.assertGreater(len(s29[k]["row"]["gated_executed"]["requires the jinja2 module"]), 0)

    def test_saved_suites_import_the_dependencies(self):
        self.assertIn("import yaml as module_2",
                      self.audit["p2/sample30"]["authors_suites"]["pynguin"]["dependency_imports"])
        self.assertIn("import jinja2.optimizer as module_2",
                      self.audit["p2/sample29"]["authors_suites"]["pynguin"]["dependency_imports"])

    def test_forms_statement_count_matches_coverage(self):
        self.assertEqual(self.audit["p2/sample29"]["statements_ast"],
                         self.audit["p2/sample29"]["authors_coverage"]["pynguin_statement"]["row"]["stmts"])


if __name__ == "__main__":
    unittest.main()
