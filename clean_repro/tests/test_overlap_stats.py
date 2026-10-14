import pytest

from cleanrepro.overlap import overlap


def test_overlap_counts():
    o = overlap({1, 2, 3, 4}, {3, 4, 5})
    assert (o["intersecting_missed"], o["union_missed"], o["only_llm_missed"], o["only_pynguin_missed"]) == (2, 5, 2, 1)


def test_stats_against_scipy():
    st = pytest.importorskip("scipy.stats")
    from cleanrepro import stats
    a, b = [90, 80, 70, 60, 85], [88, 82, 60, 65, 80]
    r = stats.compare(a, b)
    assert r["p_ttest"] == round(float(st.ttest_ind(a, b).pvalue), 4)
    assert r["p_wilcoxon"] == round(float(st.wilcoxon(a, b).pvalue), 4)
    assert stats.holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]
