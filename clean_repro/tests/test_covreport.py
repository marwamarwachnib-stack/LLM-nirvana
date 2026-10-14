from cleanrepro import covreport

STMT = """Name              Stmts   Miss  Cover   Missing
-----------------------------------------------
__init__.py           5      0   100%
decorators.py        21      8    62%   63, 66, 73-79
/Users/x/pdir/api.py 91     25    73%   12, 40-41
-----------------------------------------------
TOTAL               117     33    72%
"""
BRANCH = """Name              Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------
example.py           30      2     18      1    94%   12, 20->exit, 31->33
"""


def test_text_report_rows():
    rows = covreport.parse_text_report(STMT)
    assert set(rows) == {"__init__.py", "decorators.py", "/Users/x/pdir/api.py"}
    r = rows["decorators.py"]
    assert (r.stmts, r.miss, r.cover) == (21, 8, 62.0)
    assert r.missing_lines == [63, 66, 73, 74, 75, 76, 77, 78, 79]


def test_branch_row_and_arcs():
    r = covreport.parse_text_report(BRANCH)["example.py"]
    assert (r.branch, r.brpart, r.cover) == (18, 1, 94.0)
    assert r.missing_lines == [12]
    assert r.partial_arcs == [(20, -1), (31, 33)]


def test_find_row_by_basename():
    rows = covreport.parse_text_report(STMT)
    assert covreport.find_row(rows, "api.py").stmts == 91
    assert covreport.find_row(rows, "nothere.py") is None
