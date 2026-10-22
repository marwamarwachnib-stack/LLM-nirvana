import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cleanroom import execval, p2_externals, p2_probes, p2_validate

HAS_ENV = execval.ENV_PYTHON.exists() and shutil.which("unshare") is not None


@unittest.skipUnless(HAS_ENV, "Python 3.10.12 environment not built")
class TestClassifier(unittest.TestCase):
    """The harness must separate dependency/import failures from program exceptions."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.flat = root / "ctx" / "flat"
        self.flat.mkdir(parents=True)
        (self.flat / "prog.py").write_text("import dep\ndef f():\n    raise ValueError('program')\n"
                                           "def g():\n    return dep.Missing\ndef h():\n    dep.boom()\n")
        self.site = root / "site"
        (self.site / "dep").mkdir(parents=True)
        (self.site / "dep" / "__init__.py").write_text("def boom():\n    raise KeyError('in dependency')\n")

    def tearDown(self):
        self.tmp.cleanup()

    def probe(self, code, site=True):
        extra = [str(self.site)] if site else []
        return p2_probes.run_probe(code, ["dep"], self.flat, extra, str(self.site) if site else "",
                                   execval.ENV_PYTHON)["result"]

    def test_ok(self):
        r = self.probe("import prog\nresult = 1")
        self.assertEqual((r["outcome"], r["result"]), ("OK", "1"))

    def test_dependency_import_error(self):
        self.assertEqual(self.probe("import prog", site=False)["outcome"], "DEPENDENCY_IMPORT_ERROR")

    def test_context_import_error(self):
        r = self.probe("import not_in_context_xyz")
        self.assertEqual(r["outcome"], "CONTEXT_IMPORT_ERROR")

    def test_dependency_api_missing(self):
        r = self.probe("import prog\nprog.g()")
        self.assertEqual(r["outcome"], "DEPENDENCY_API_MISSING")
        self.assertEqual(r["innermost"][:2], ["prog.py", 5])

    def test_exception_in_dependency_code(self):
        self.assertEqual(self.probe("import prog\nprog.h()")["outcome"], "EXCEPTION_IN_DEPENDENCY_CODE")

    def test_program_exception(self):
        r = self.probe("import prog\nprog.f()")
        self.assertEqual((r["outcome"], r["exc_type"]), ("PROGRAM_EXCEPTION", "builtins.ValueError"))

    def test_exception_in_probe_code_is_other(self):
        self.assertEqual(self.probe("raise RuntimeError('x')")["outcome"], "OTHER_EXCEPTION")


class TestMatching(unittest.TestCase):
    def test_matches(self):
        self.assertTrue(p2_probes.matches({"outcome": "OK", "result": "'6.0.1'"}, "OK", "'6.0.1'"))
        self.assertFalse(p2_probes.matches({"outcome": "OK", "result": "'6.0'"}, "OK", "'6.0.1'"))
        self.assertTrue(p2_probes.matches({"outcome": "PROGRAM_EXCEPTION", "exc_type": "base.ParseError",
                                           "message": "m"}, "PROGRAM_EXCEPTION", "ParseError"))
        self.assertFalse(p2_probes.matches({"outcome": "CONTEXT_IMPORT_ERROR"}, "EXCEPTION_IN_DEPENDENCY_CODE", None))

    def test_probes_are_pre_registered_for_both_samples(self):
        self.assertEqual(sorted(p2_probes.PROBES), ["p2/sample29", "p2/sample30"])
        ids = [p[0] for s in p2_probes.PROBES.values() for p in s["probes"]]
        self.assertEqual(len(ids), len(set(ids)))


class TestScopedSites(unittest.TestCase):
    def test_sample_scoped_site_wins_and_does_not_leak(self):
        ext = {"results": {"typesystem==0.2.4": {"status": "INSTALLED", "site": "/wide"},
                           "typesystem==0.2.4@sample29": {"status": "INSTALLED", "site": "/s29"}}}
        d = {"release_set": ["0.2.4"]}
        self.assertEqual(p2_validate.site_for("typesystem", d, ext, "sample29"), "/s29")
        self.assertEqual(p2_validate.site_for("typesystem", d, ext, "sample30"), "/wide")
        only_scoped = {"results": {"typesystem==0.2.4@sample29": {"status": "INSTALLED", "site": "/s29"}}}
        self.assertIsNone(p2_validate.site_for("typesystem", d, only_scoped, "sample30"))
        self.assertIsNone(p2_validate.site_for("typesystem", {"release_set": ["0.2.3"]}, ext, "sample29"))


class TestApprovedPins(unittest.TestCase):
    def test_pin_must_be_newest_before_cutoff(self):
        spec = {"approved_additions": ["Jinja2==3.1.2"], "import_names": {"jinja2": "Jinja2"}}
        with mock.patch.object(p2_externals, "pypi_json", return_value={}), \
                mock.patch.object(p2_externals, "newest_before", return_value="3.1.3"), \
                mock.patch.object(p2_externals, "first_upload", return_value="2022-04-28T00:00:00"), \
                mock.patch.object(p2_externals, "resolve_lock", side_effect=AssertionError("must not resolve")):
            with self.assertRaises(RuntimeError):
                p2_externals.install_approved("typesystem==0.2.4@sample29", spec, "2024-01-26T16:51:11", [])

    def test_lock_path_is_sample_scoped(self):
        self.assertEqual(p2_externals.lock_path("typesystem==0.2.4@sample29").name, "typesystem-0.2.4-sample29.txt")


class TestRecordedProbeRun(unittest.TestCase):
    """The committed probe run must show the documented outcomes."""

    def test_markup_limitation_recorded(self):
        runs = sorted((execval.RUNS_DIR.parent / "probes").glob("*/probes.json"))
        superseded = (execval.RUNS_DIR.parent / "SUPERSEDED.md").read_text()
        runs = [r for r in runs if r.parent.name not in superseded]
        if not runs:
            self.skipTest("no probe run")
        data = json.loads(runs[-1].read_text())
        p = {x["id"]: x for x in data["programs"]["p2/sample29"]["probes"]}
        self.assertEqual(p["29.3"]["outcome"], "DEPENDENCY_API_MISSING")
        self.assertEqual(p["29.3"]["first_result"]["innermost"][:2], ["forms.py", 109])
        self.assertTrue(all(x["consistent"] for prog in data["programs"].values() for x in prog["probes"]))


if __name__ == "__main__":
    unittest.main()
