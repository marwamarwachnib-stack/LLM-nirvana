import csv
import unittest

from cleanroom import eligibility, manifest, paths


def row(pid, status, in_scope="True", s="small", cat="cat2_functions"):
    return {"program_id": pid, "set": s, "category": cat, "in_scope": in_scope,
            "status": status, "reasons": "why"}


class TestCombine(unittest.TestCase):
    def test_every_row_kept_with_explicit_outcome(self):
        rows = [row("a", manifest.CANDIDATE), row("b", manifest.NEEDS_DECISION_STDIN),
                row("c", manifest.OUT_OF_SCOPE, in_scope="False", s="p1"),
                row("d", manifest.PENDING_CONTEXT, s="p2", cat="unlabelled")]
        results = {"a": {"execution_verified": True, "outcome": "VERIFIED_IMPORT_AND_DEVTESTS",
                         "outcome_reason": "ok", "v1_import": {"consistent": True},
                         "v2a_as_shipped": {"passed": 0, "tests": 4},
                         "v2b_reference": {"passed": 4, "tests": 4, "skipped": 0},
                         "solution_module": {"evidence": "config.json files.solution"}}}
        evidence = [{"program_id": "d", "import": "cfg", "classification": "SIBLING_IN_AUTHORS_RUN"}]
        out = {t["program_id"]: t for t in eligibility.combine(rows, "RUN", results, evidence)}
        ctx = eligibility.combine(rows, "RUN", results, evidence,
                                  {"d": {"project": "p", "release_set": ["1.0"], "decision": "RESOLVED", "reason": ""}},
                                  "CTX", {"d": {"execution_verified": True, "outcome": "VERIFIED_IMPORT_WITH_CONTEXT",
                                                "outcome_reason": "ok", "v1_import": {"consistent": True}}})
        d = [t for t in ctx if t["program_id"] == "d"][0]
        self.assertEqual((d["attempted"], d["run_id"], d["p2_release_set"], d["p2_context_decision"]),
                         (True, "CTX", "1.0", "RESOLVED"))
        self.assertEqual(out["a"]["devtest_oracle"].split()[0], "EVIDENCE_BACKED_REFERENCE")
        self.assertEqual(list(out), ["a", "b", "c", "d"])
        self.assertEqual((out["a"]["execution_verified"], out["a"]["devtests_as_shipped"],
                          out["a"]["devtests_vs_example"], out["a"]["run_id"]), (True, "0/4", "4/4", "RUN"))
        for pid in "bcd":
            self.assertEqual((out[pid]["attempted"], out[pid]["execution_verified"], out[pid]["outcome"]),
                             (False, False, "NOT_ATTEMPTED"))
        self.assertIn("out of scope", out["c"]["outcome_reason"])
        self.assertIn(manifest.NEEDS_DECISION_STDIN, out["b"]["outcome_reason"])
        self.assertEqual(out["d"]["p2_import_evidence"], "cfg=SIBLING_IN_AUTHORS_RUN")


@unittest.skipUnless(eligibility.ELIGIBILITY_CSV.exists(), "eligibility not built yet")
class TestRealEligibility(unittest.TestCase):
    def test_all_manifest_rows_present(self):
        with open(eligibility.ELIGIBILITY_CSV, encoding="utf-8", newline="") as f:
            table = list(csv.DictReader(f))
        ids = [r["program_id"] for r in manifest.read_manifest(paths.MANIFEST_CSV)]
        self.assertEqual([t["program_id"] for t in table], ids)
        in_scope = [t for t in table if t["in_scope"] == "True"]
        self.assertEqual(len(in_scope), 103)
        attempted = [t for t in in_scope if t["attempted"] == "True"]
        self.assertTrue(all(t["static_status"] == manifest.CANDIDATE
                            or (t["static_status"] == manifest.PENDING_CONTEXT
                                and t["p2_context_decision"] == "RESOLVED") for t in attempted))
        self.assertTrue(all(t["attempted"] == "False" for t in table
                            if t["p2_context_decision"].startswith("UNRESOLVED")))
        self.assertTrue(all(t["outcome"] == "NOT_ATTEMPTED" for t in table
                            if t["category"] == "cat1_scripts"))  # Cat 1 deferred
        self.assertTrue(all(t["outcome"] == "NOT_ATTEMPTED" for t in table if t["attempted"] == "False"))
        self.assertTrue(all(t["execution_verified"] == "False" for t in table if t["attempted"] == "False"))


if __name__ == "__main__":
    unittest.main()
