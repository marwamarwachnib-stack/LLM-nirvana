"""Paper-style analysis of Phase 1 results (reads results/iterations.csv, results/jobs.csv and run folders).

Outputs in results/ (or results/<prefix>_* with --prefix):
  table_coverage.csv     Tables 1/2   avg statement / branch coverage per category and tool (iteration 1)
  stats_tests.csv        §3.1/§3.2.1  t-test (paper) + Mann-Whitney U, each LLM vs Pynguin, per category
  table_iterations.csv   Table 3      iteration-1 / iteration-5 / best coverage, best-least, median iterations
  table_assertions.csv   Table 4      % incorrect assertions and breakdown (final suites)
  overlap.csv            Table 5      per program x tool pair: missed-statement overlap, Jaccard, combined coverage
  table_overlap.csv      Table 5      averages per category and pair
  complexity_corr.csv    Fig. 5       Spearman / Pearson of coverage vs max McCabe per tool
  table_energy.csv       (new)        time and energy per tool
  fig4_*.png fig5_*.png fig6_iterations.png fig7_overlap.png

Usage: .venv/bin/python scripts/analyze.py [--prefix pilot]
"""
import argparse
import itertools
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from common import RESULTS, RUNS, read_json  # noqa: E402

# fixed categorical slots (reference palette, slots 1-4); color follows the tool, never its rank
TOOL_COLORS = {"pynguin": "#2a78d6", "dsc-6.7b": "#eb6834", "cl-7b": "#1baf7a", "dsc-1.3b": "#eda100"}
TOOL_ORDER = ["pynguin", "dsc-6.7b", "cl-7b", "dsc-1.3b"]
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dd"


def style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED)


def tools_in(df):
    return [t for t in TOOL_ORDER if t in set(df["tool"])] + sorted(set(df["tool"]) - set(TOOL_ORDER))


# ----------------------------------------------------------------------------- missed-line sets

def missed_sets():
    """{(tool, category, program, seed_or_None, 'iter1'|'final'): (missed set, n_statements, refactored)}"""
    out = {}
    for m in RUNS.glob("pynguin/*/*/seed*/metrics.json"):
        if not (m.parent / "DONE").exists():
            continue
        d = read_json(m)
        v = (set(d["coverage"]["missing_lines"]), d["coverage"]["num_statements"], False)
        for which in ("iter1", "final"):
            out[("pynguin", d["category"], d["program"], d["seed"], which)] = v
    for job in RUNS.glob("*/*/*/rep0/job.json"):
        j = read_json(job)
        if j.get("status") != "done":
            continue
        for which, k in (("iter1", 1), ("final", j["n_iterations"])):
            d = read_json(job.parent / f"iter{k}" / "metrics.json")
            out[(j["tool"], j["category"], j["program"], None, which)] = (
                set(d["coverage"]["missing_lines"]), d["coverage"]["num_statements"], d.get("refactored_module", False))
    return out


def overlap_rows(ms):
    rows = []
    keys = {(t, c, p, w) for (t, c, p, s, w) in ms}
    progs = {(c, p) for (_, c, p, _) in keys}
    tools = sorted({t for (t, _, _, _) in keys})
    for (c, p), which in itertools.product(sorted(progs), ("iter1", "final")):
        def variants(tool):
            if tool == "pynguin":
                return [(s, ms[k]) for k in ms for s in [k[3]] if k[0] == "pynguin" and k[1:3] == (c, p) and k[4] == which]
            k = (tool, c, p, None, which)
            return [(None, ms[k])] if k in ms else []
        for a, b in itertools.combinations(tools, 2):
            for (sa, A), (sb, B) in itertools.product(variants(a), variants(b)):
                if A[2] or B[2]:  # refactored Cat-1 module: line numbers not comparable
                    continue
                inter, union = A[0] & B[0], A[0] | B[0]
                n = A[1] or 0
                rows.append({
                    "category": c, "program": p, "which": which, "tool_a": a, "tool_b": b, "seed_a": sa, "seed_b": sb,
                    "missed_a": len(A[0]), "missed_b": len(B[0]), "intersecting_missed": len(inter),
                    "union_missed": len(union), "minimum_missed": min(len(A[0]), len(B[0])),
                    "minimum_covered": min(len(A[0]), len(B[0])) - len(inter),
                    "maximum_covered": len(union) - len(inter),
                    "jaccard": len(inter) / len(union) if union else None,
                    "combined_stmt_cov": round(100 * (n - len(inter)) / n, 2) if n else None,
                    "best_single_stmt_cov": round(100 * (n - min(len(A[0]), len(B[0]))) / n, 2) if n else None,
                })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="")
    args = ap.parse_args()
    pre = f"{args.prefix}_" if args.prefix else ""
    out = lambda name: RESULTS / f"{pre}{name}"  # noqa: E731
    it = pd.read_csv(RESULTS / "iterations.csv")
    jobs = pd.read_csv(RESULTS / "jobs.csv")
    tools = tools_in(jobs)

    # Tables 1/2 (RQ1, iteration 1). Pynguin: mean over seeds per program first.
    per_prog = jobs.groupby(["tool", "category", "program"], as_index=False)[
        ["stmt_cov", "branch_cov", "stmt_branch_cov", "mccabe_max"]].mean()
    tab = per_prog.groupby(["category", "tool"])[["stmt_cov", "branch_cov", "stmt_branch_cov"]].agg(["mean", "std", "count"]).round(2)
    tab.to_csv(out("table_coverage.csv"))

    # statistics: each LLM vs Pynguin per category (paper: independent t-test)
    srows = []
    for cat in sorted(per_prog["category"].unique()):
        py = per_prog[(per_prog.tool == "pynguin") & (per_prog.category == cat)]
        for t in tools:
            if t == "pynguin":
                continue
            ll = per_prog[(per_prog.tool == t) & (per_prog.category == cat)]
            for metric in ("stmt_cov", "branch_cov"):
                a, b = ll[metric].dropna(), py[metric].dropna()
                row = {"category": cat, "tool": t, "metric": metric, "n_llm": len(a), "n_pynguin": len(b),
                       "mean_llm": a.mean(), "mean_pynguin": b.mean()}
                if len(a) >= 2 and len(b) >= 2:
                    row["ttest_p"] = stats.ttest_ind(a, b, equal_var=False).pvalue
                    row["mannwhitney_p"] = stats.mannwhitneyu(a, b).pvalue
                srows.append(row)
    pd.DataFrame(srows).to_csv(out("stats_tests.csv"), index=False)

    # Table 3 (RQ2): iterative improvement (LLM tools)
    llm_it = it[it.tool != "pynguin"]
    if not llm_it.empty:
        g = llm_it.groupby(["tool", "category", "program"])
        chain = g.agg(iter1=("stmt_cov", "first"), last=("stmt_cov", "last"), best=("stmt_cov", "max"),
                      least=("stmt_cov", "min"), n_iter=("iteration", "max")).reset_index()
        chain["iter5_or_last"] = chain["last"]
        chain["best_minus_least"] = chain["best"] - chain["least"]
        chain.groupby(["tool", "category"]).agg(
            avg_iter1=("iter1", "mean"), avg_iter5_or_last=("iter5_or_last", "mean"), avg_best=("best", "mean"),
            avg_best_minus_least=("best_minus_least", "mean"), median_iters_to_plateau=("n_iter", "median"),
            n=("program", "count")).round(2).to_csv(out("table_iterations.csv"))
        # Fig. 6: average statement coverage per iteration (carry last value forward after stopping)
        fig, ax = plt.subplots(figsize=(7, 4))
        for t in tools_in(llm_it):
            sub = llm_it[llm_it.tool == t].pivot_table(index=["category", "program"], columns="iteration", values="stmt_cov")
            sub = sub.reindex(columns=range(1, int(llm_it.iteration.max()) + 1)).ffill(axis=1)
            mean = sub.mean()
            ax.plot(mean.index, mean.values, color=TOOL_COLORS.get(t), linewidth=2, marker="o", markersize=8, label=t)
            ax.annotate(t, (mean.index[-1], mean.values[-1]), xytext=(6, 0), textcoords="offset points", color=INK, fontsize=9, va="center")
        style(ax, "Average statement coverage per iteration (Fig. 6)", "iteration", "statement coverage (%)")
        ax.set_ylim(0, 105)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(out("fig6_iterations.png"), dpi=150)
        plt.close(fig)

    # Table 4 (RQ3): incorrect assertions on the final suites
    a = jobs.groupby(["tool", "category"])[["final_incorrect_assert_pct", "final_incorrect_pct_assertion_error",
                                            "final_incorrect_pct_try_except", "final_incorrect_pct_runtime"]].mean().round(2)
    e = jobs.groupby(["tool", "category"])[["n_collection_error_files", "n_syntax_error_files"]].mean().round(2)
    a.join(e).to_csv(out("table_assertions.csv"))

    # Table 5 / Fig. 7 (RQ4): overlap of missed statements
    ov = overlap_rows(missed_sets())
    if not ov.empty:
        ov.to_csv(out("overlap.csv"), index=False)
        # average over Pynguin seeds per program first, then over programs
        cols = ["missed_a", "missed_b", "intersecting_missed", "union_missed", "minimum_missed", "minimum_covered", "maximum_covered",
                "jaccard", "combined_stmt_cov", "best_single_stmt_cov"]
        pp = ov.groupby(["which", "tool_a", "tool_b", "category", "program"], as_index=False)[cols].mean()
        t5 = pp.groupby(["which", "tool_a", "tool_b", "category"])[cols].mean().round(2)
        t5["n_programs"] = pp.groupby(["which", "tool_a", "tool_b", "category"]).size()
        t5["n_jaccard_undefined"] = pp.groupby(["which", "tool_a", "tool_b", "category"])["jaccard"].apply(lambda s: s.isna().sum())
        t5.to_csv(out("table_overlap.csv"))
        sel = pp[(pp.which == "iter1") & ((pp.tool_a == "pynguin") | (pp.tool_b == "pynguin"))]
        if not sel.empty:
            pairs = sel.groupby(["tool_a", "tool_b"])
            fig, axes = plt.subplots(len(pairs), 1, figsize=(8, 2.6 * len(pairs)), squeeze=False)
            for ax, ((ta, tb), sub) in zip(axes[:, 0], pairs):
                x = range(len(sub))
                only_a = sub["missed_a"] - sub["intersecting_missed"]
                only_b = sub["missed_b"] - sub["intersecting_missed"]
                w = 0.27
                ax.bar([i - w for i in x], only_a, w * 0.92, color=TOOL_COLORS.get(ta), label=f"missed only by {ta}")
                ax.bar(list(x), sub["intersecting_missed"], w * 0.92, color=MUTED, label="missed by both")
                ax.bar([i + w for i in x], only_b, w * 0.92, color=TOOL_COLORS.get(tb), label=f"missed only by {tb}")
                ax.set_xticks(list(x), sub["program"], rotation=30, ha="right", fontsize=8)
                style(ax, f"Missed statements: {ta} vs {tb} (iteration 1, Fig. 7)", "", "statements")
                ax.legend(frameon=False, fontsize=8)
            fig.tight_layout()
            fig.savefig(out("fig7_overlap.png"), dpi=150)
            plt.close(fig)

    # Fig. 5: coverage vs max McCabe, with correlations (added: the paper only plotted it)
    crows = []
    for metric in ("stmt_cov", "branch_cov"):
        fig, ax = plt.subplots(figsize=(7, 4))
        for t in tools:
            sub = per_prog[per_prog.tool == t].dropna(subset=["mccabe_max", metric])
            ax.scatter(sub["mccabe_max"], sub[metric], s=64, color=TOOL_COLORS.get(t), edgecolor="white", linewidth=2, label=t, alpha=0.9)
            if len(sub) >= 3 and sub["mccabe_max"].nunique() > 1:
                rho = stats.spearmanr(sub["mccabe_max"], sub[metric])
                r = stats.pearsonr(sub["mccabe_max"], sub[metric]) if sub[metric].nunique() > 1 else None
                crows.append({"tool": t, "metric": metric, "n": len(sub), "spearman_rho": rho.statistic, "spearman_p": rho.pvalue,
                              "pearson_r": r and r.statistic, "pearson_p": r and r.pvalue})
        style(ax, f"{'Statement' if metric == 'stmt_cov' else 'Branch'} coverage vs max McCabe complexity (Fig. 5)",
              "max McCabe complexity of the module", "coverage (%)")
        ax.set_ylim(-3, 105)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(out(f"fig5_{metric}_vs_mccabe.png"), dpi=150)
        plt.close(fig)
    pd.DataFrame(crows).to_csv(out("complexity_corr.csv"), index=False)

    # Fig. 4: per-program coverage (iteration 1)
    for metric in ("stmt_cov", "branch_cov"):
        progs = sorted(per_prog["program"].unique())
        fig, ax = plt.subplots(figsize=(max(7, 0.5 * len(progs) * len(tools)), 4))
        w = 0.8 / len(tools)
        for i, t in enumerate(tools):
            sub = per_prog[per_prog.tool == t].set_index("program").reindex(progs)
            ax.bar([j + (i - (len(tools) - 1) / 2) * w for j in range(len(progs))], sub[metric].fillna(0), w * 0.92,
                   color=TOOL_COLORS.get(t), label=t)
        ax.set_xticks(range(len(progs)), progs, rotation=30, ha="right", fontsize=8)
        style(ax, f"{'Statement' if metric == 'stmt_cov' else 'Branch'} coverage per program, iteration 1 (Fig. 4)", "", "coverage (%)")
        ax.set_ylim(0, 105)
        ax.legend(frameon=False, ncol=len(tools), fontsize=8)
        fig.tight_layout()
        fig.savefig(out(f"fig4_{metric}.png"), dpi=150)
        plt.close(fig)

    # energy / time (new). LLM: the whole iteration chain; Pynguin: one seed run.
    # Headline = RAPL package Wh (net of idle) + RAPL DRAM Wh; CodeCarbon CPU is kept as a cross-check (decision 9).
    jobs = jobs.copy()  # de-fragment before adding the energy columns
    def col(chain, single):
        c = jobs[chain] if chain in jobs else pd.Series(index=jobs.index, dtype=float)
        return c.where(jobs.tool != "pynguin").fillna(jobs[single] if single in jobs else float("nan"))
    jobs["gen_s"] = col("chain_gen_wall_s", "gen_wall_s")
    jobs["rapl_pkg_wh"] = col("chain_gen_rapl_msr_pkg_wh", "gen_rapl_msr_pkg_wh")
    jobs["rapl_pkg_wh_net"] = col("chain_gen_rapl_pkg_wh_net", "gen_rapl_pkg_wh_net")
    jobs["rapl_dram_wh"] = col("chain_gen_rapl_msr_dram_wh", "gen_rapl_msr_dram_wh")
    jobs["cc_cpu_wh"] = col("chain_gen_cc_cpu_wh", "gen_cc_cpu_wh")
    jobs["load_s"] = col("chain_load_wall_s", "load_wall_s")
    jobs["load_rapl_pkg_wh"] = col("chain_load_rapl_msr_pkg_wh", "load_rapl_msr_pkg_wh")
    agg = dict(n=("program", "count"), gen_s=("gen_s", "mean"), rapl_pkg_wh=("rapl_pkg_wh", "mean"),
               rapl_pkg_wh_net=("rapl_pkg_wh_net", "mean"), rapl_dram_wh=("rapl_dram_wh", "mean"),
               cc_cpu_wh=("cc_cpu_wh", "mean"), load_s=("load_s", "mean"), load_rapl_pkg_wh=("load_rapl_pkg_wh", "mean"),
               iter1_gen_s=("gen_wall_s", "mean"), final_stmt_cov=("final_stmt_cov", "mean"))
    if "tokens_per_s" in jobs:
        agg["iter1_tokens_per_s"] = ("tokens_per_s", "mean")
    en = jobs.groupby(["tool", "category"]).agg(**agg).round(4)
    en.to_csv(out("table_energy.csv"))
    print("analysis written to", RESULTS)


if __name__ == "__main__":
    main()
