import tempfile
import unittest
from pathlib import Path

from cleanroom import manifest, p2_evidence as ev

REPORT = """Name            Stmts   Miss  Cover   Missing
---------------------------------------------
__init__.py         0      0   100%
api.py             57     16    72%   71-76
cfg.py             44     15    66%   61
pkg/__init__.py     3      0   100%
pkg\\sub.py         5      0   100%
test_api.py        41      0   100%
---------------------------------------------
TOTAL             361    135    63%
"""


class TestReportParsing(unittest.TestCase):
    def test_report_modules(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "statement_coverage_api.txt"
            p.write_text(REPORT)
            names = ev.report_modules(p)
        self.assertEqual(names, {"__init__", "api", "cfg", "pkg", "pkg.sub", "test_api"})


class TestClassify(unittest.TestCase):
    def test_rules(self):
        listed = {"cfg", "decorators"}
        self.assertEqual(ev.classify("cfg", listed, None), ev.SIBLING_IN_AUTHORS_RUN)
        self.assertEqual(ev.classify(".decorators", listed, None), ev.SIBLING_IN_AUTHORS_RUN)
        self.assertEqual(ev.classify(".other", listed, None), ev.SIBLING_BY_RELATIVE_IMPORT)
        old = {"exists": True, "first_upload_utc": "2016-01-01T00:00:00"}
        new = {"exists": True, "first_upload_utc": "2025-03-01T00:00:00"}
        self.assertEqual(ev.classify("stringcase", listed, old), ev.EXTERNAL_PACKAGE_CANDIDATE)
        self.assertEqual(ev.classify("context", listed, new), ev.NO_EVIDENCE)  # post-dates snapshot
        self.assertEqual(ev.classify("x", listed, {"exists": True, "first_upload_utc": None}), ev.NO_EVIDENCE)
        self.assertEqual(ev.classify("zzz", listed, {"exists": False}), ev.NO_EVIDENCE)
        self.assertEqual(ev.classify("zzz", listed, {"exists": None}), ev.NO_EVIDENCE)


class TestBuild(unittest.TestCase):
    def test_build_with_fake_pypi(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            s = repo / manifest.P2_ROOT / manifest.P2_MODULE_DIR / "sample37"
            s.mkdir(parents=True)
            (s / "statement_coverage_api.txt").write_text(REPORT)
            c = repo / manifest.P2_ROOT / manifest.P2_CHATGPT_DIR / "sample37"
            c.mkdir(parents=True)
            (c / "statement_coverage.txt").write_text("Name Stmts\nmm.py 3 0 100%\n")
            rows = [
                {"program_id": "p2/sample37", "set": "p2", "name": "sample37",
                 "status": manifest.PENDING_CONTEXT, "target": f"{s}/api.py",
                 "imports_unresolved": "cfg;mm;stringcase;nothing", "imports_relative": ".rel",
                 "imports_optional_unresolved": ""},
                {"program_id": "p2/sample1", "set": "p2", "name": "sample1",
                 "status": manifest.CANDIDATE, "target": "x/cfg.py",
                 "imports_unresolved": "", "imports_relative": "", "imports_optional_unresolved": ""},
            ]
            calls = []

            def fake(name):
                calls.append(name)
                return {"status": 200, "exists": True, "project": name,
                        "first_upload_utc": "2016-01-01T00:00:00"} if name == "stringcase" \
                    else {"status": 404, "exists": False}

            out, cache = ev.build(rows, query=fake, repo=repo)
        by = {e["import"]: e for e in out}
        self.assertEqual(by["cfg"]["classification"], ev.SIBLING_IN_AUTHORS_RUN)
        self.assertEqual(by["cfg"]["same_name_elsewhere_in_snapshot"], "p2/sample1")
        self.assertEqual(by["mm"]["classification"], ev.SIBLING_IN_AUTHORS_RUN)  # from ChatGPT report
        self.assertEqual(by["stringcase"]["classification"], ev.EXTERNAL_PACKAGE_CANDIDATE)
        self.assertEqual(by["nothing"]["classification"], ev.NO_EVIDENCE)
        self.assertEqual(by[".rel"]["classification"], ev.SIBLING_BY_RELATIVE_IMPORT)
        self.assertEqual(sorted(calls), ["nothing", "stringcase"])  # siblings never queried
        self.assertEqual(len(out), 5)  # CANDIDATE rows are skipped


if __name__ == "__main__":
    unittest.main()
