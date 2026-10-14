from cleanrepro import iterate


def fake(covers, missing):
    calls = {"prompts": []}

    def generate(k, prompt):
        calls["prompts"].append(prompt)
        return f"reply {k}"

    def extract_and_write(k, reply):
        return "ok", f"test_iter{k}.py"

    def evaluate(files):
        k = len(files)
        return {"stmt_cover": covers[k - 1], "stmt_cover_report": int(covers[k - 1]),
                "missing_lines": missing[k - 1], "branch_cover": covers[k - 1]}
    return calls, generate, extract_and_write, evaluate


def test_stops_when_no_improvement():
    calls, g, e, ev = fake([60.0, 80.0, 80.0, 90.0], [[1, 2], [3], [3], [4]])
    r = iterate.run("x = 1\n", g, e, ev, 5, lambda files: "SUITE")
    assert [x.k for x in r.records] == [1, 2, 3]
    assert r.stop_reason == "no improvement over previous iteration"
    assert r.coverage_by_iteration() == [60.0, 80.0, 80.0, 80.0, 80.0]
    assert "only give 60% coverage" in calls["prompts"][1] and "- 1-2" in calls["prompts"][1]
    assert "SUITE" in calls["prompts"][1]


def test_stops_at_full_coverage():
    calls, g, e, ev = fake([70.0, 100.0], [[5], []])
    r = iterate.run("x = 1\n", g, e, ev, 5, lambda f: "")
    assert len(r.records) == 2 and r.stop_reason == "no missed statement left"


def test_stops_after_five():
    calls, g, e, ev = fake([10.0, 20.0, 30.0, 40.0, 50.0, 60.0], [[1]] * 6)
    r = iterate.run("x = 1\n", g, e, ev, 5, lambda f: "")
    assert len(r.records) == 5 and r.stop_reason == "maximum of 5 iterations"


def test_failed_extraction_counts_as_no_improvement():
    def generate(k, p):
        return ""

    def extract_and_write(k, reply):
        return ("ok", "test_iter1.py") if k == 1 else ("no_code", None)

    def evaluate(files):
        return {"stmt_cover": 50.0, "stmt_cover_report": 50, "missing_lines": [9]}
    r = iterate.run("x = 1\n", generate, extract_and_write, evaluate, 5, lambda f: "")
    assert len(r.records) == 2 and r.records[1].extraction_status == "no_code"
    assert r.stop_reason == "no improvement over previous iteration"
