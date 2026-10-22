import tempfile
import unittest
from pathlib import Path

from cleanroom import a9_paper_check as a9, paths


class TestHelpers(unittest.TestCase):
    def test_trunc_and_compare(self):
        self.assertEqual(a9.trunc(88.7778), 88.77)
        self.assertEqual(a9.trunc(77.4375, 1), 77.4)
        r = a9.compare_row((88.7778, 79.5938), (88.77, 79.6))
        self.assertEqual((r[0]["equal_truncated"], r[0]["equal_rounded"]), (True, False))
        self.assertEqual((r[1]["equal_truncated"], r[1]["equal_rounded"]), (False, True))

    def test_module_row_prefers_relative_and_accepts_absolute(self):
        with tempfile.TemporaryDirectory() as d:
            rep = Path(d) / "statement_coverage.txt"
            rep.write_text("Name  Stmts   Miss  Cover   Missing\n\r\r\n"
                           "/Users/x/pkg/api.py   57   16   72%   1-3\n")
            r = a9.module_row([rep], "api.py")
            self.assertEqual((r["value"], r["absolute"]), (72.0, True))
            rep.write_text("Name  Stmts   Miss  Cover   Missing\n/Users/x/pkg/api.py 57 16 72% 1\napi.py 50 5 90% 2\n")
            r = a9.module_row([rep], "api.py")
            self.assertEqual((r["value"], r["absolute"]), (90.0, False))
            self.assertIsNone(a9.module_row([rep], "other.py"))


@unittest.skipUnless((paths.REPO_ROOT / "100_300 LOC p2").is_dir(), "snapshot not present")
class TestSnapshotAgainstPaper(unittest.TestCase):
    """Verified findings reported in A9 must hold on the snapshot."""

    @classmethod
    def setUpClass(cls):
        cls.t2 = a9.check_table2(a9.saved_p2())
        cls.t1 = a9.check_table1(a9.saved_small())

    def test_41_samples_and_missing_8_10(self):
        self.assertEqual(self.t2["samples_with_all_four_values"], 41)
        self.assertEqual(self.t2["samples_missing_a_value"], ["sample8", "sample10"])

    def test_chatgpt_all_row_matches_truncated(self):
        row = self.t2["all_available_vs_paper_all40"]
        self.assertTrue(row[0]["equal_truncated"] and row[2]["equal_truncated"])
        self.assertFalse(row[3]["equal_truncated"] or row[3]["equal_rounded"])  # Pynguin branch differs
        self.assertEqual(self.t2["size40_subsets_matching_all_four"], [])

    def test_category2_candidate_rule_matches(self):
        c2 = self.t2["candidate_rule"]["category2"]
        self.assertEqual(c2["n"], 9)
        self.assertTrue(all(v["equal_truncated"] for v in c2["vs_paper"]))

    def test_table1_pynguin_not_reproduced(self):
        for cat in ("cat2_functions", "cat3_classes"):
            r = self.t1[cat]
            self.assertNotAlmostEqual(r["pynguin_stmt_mean"], r["paper_pynguin_stmt"], delta=0.05)


if __name__ == "__main__":
    unittest.main()
