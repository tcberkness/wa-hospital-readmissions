"""Statistical comparison of Washington hospitals with the rest of the US, plus
hospital-level observed/expected flags and funnel-plot control limits for Tableau.

Usage:  python src/analysis.py   (run after build_db.py)
"""
from __future__ import annotations

import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from common import DB_PATH, FIGURES, MEASURE_LABELS, PROCESSED


def bh_adjust(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg false discovery rate adjustment."""
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(adj, 0, 1)
    return out


def state_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """For each measure: WA mean ERR with 95% CI, one-sample test vs 1.0,
    and Welch t-test / Mann-Whitney vs hospitals in all other states."""
    rows = []
    for m, g in df.dropna(subset=["excess_readmission_ratio"]).groupby("measure_name"):
        wa = g.loc[g.state == "WA", "excess_readmission_ratio"].to_numpy()
        us = g.loc[g.state != "WA", "excess_readmission_ratio"].to_numpy()
        if len(wa) < 3:
            continue
        ci = stats.t.interval(0.95, len(wa) - 1, loc=wa.mean(), scale=stats.sem(wa))
        us_ci = stats.t.interval(0.95, len(us) - 1, loc=us.mean(), scale=stats.sem(us))
        welch = stats.ttest_ind(wa, us, equal_var=False)
        mw = stats.mannwhitneyu(wa, us, alternative="two-sided")
        pooled_sd = np.sqrt(((len(wa) - 1) * wa.var(ddof=1) + (len(us) - 1) * us.var(ddof=1))
                            / (len(wa) + len(us) - 2))
        rows.append({
            "measure_name": m,
            "measure_label": MEASURE_LABELS.get(m, m),
            "wa_hospitals": len(wa),
            "wa_mean_err": wa.mean(),
            "wa_ci_low": ci[0],
            "wa_ci_high": ci[1],
            "other_states_hospitals": len(us),
            "other_states_mean_err": us.mean(),
            "other_ci_low": us_ci[0],
            "other_ci_high": us_ci[1],
            "difference": wa.mean() - us.mean(),
            "cohens_d": (wa.mean() - us.mean()) / pooled_sd,
            "p_vs_1": stats.ttest_1samp(wa, 1.0).pvalue,
            "p_welch": welch.pvalue,
            "p_mannwhitney": mw.pvalue,
        })
    out = pd.DataFrame(rows)
    out["p_welch_bh"] = bh_adjust(out["p_welch"])
    out["significant_fdr_05"] = out["p_welch_bh"] < 0.05
    return out.sort_values("difference")


def poisson_ci(o: np.ndarray, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Exact (Garwood) Poisson confidence interval for an observed count."""
    lo = np.where(o > 0, stats.chi2.ppf(alpha / 2, 2 * o) / 2, 0.0)
    hi = stats.chi2.ppf(1 - alpha / 2, 2 * (o + 1)) / 2
    return lo, hi


def hospital_flags(wa: pd.DataFrame) -> pd.DataFrame:
    """Observed/expected readmissions per WA hospital and measure, with an exact
    95% CI. 'Higher than expected' only when the whole interval is above 1."""
    d = wa.dropna(subset=["number_of_readmissions", "expected_readmissions"]).copy()
    d = d[d.expected_readmissions > 0]
    o = d["number_of_readmissions"].to_numpy()
    lo, hi = poisson_ci(o)
    d["oe_ratio"] = o / d["expected_readmissions"]
    d["oe_ci_low"] = lo / d["expected_readmissions"]
    d["oe_ci_high"] = hi / d["expected_readmissions"]
    d["oe_flag"] = np.select(
        [d.oe_ci_low > 1, d.oe_ci_high < 1],
        ["Higher than expected", "Lower than expected"],
        "As expected",
    )
    return d


def funnel_limits(wa: pd.DataFrame) -> pd.DataFrame:
    """95% and 99.8% control limits for O/E = 1 across a range of expected counts."""
    rows = []
    for m, g in wa.dropna(subset=["expected_readmissions"]).groupby("measure_label"):
        top = max(g["expected_readmissions"].max() * 1.1, 5)
        for e in np.linspace(1, top, 80):
            row = {"measure_label": m, "expected_readmissions": e}
            for name, a in [("95", 0.05), ("998", 0.002)]:
                row[f"lower_{name}"] = stats.poisson.ppf(a / 2, e) / e
                row[f"upper_{name}"] = stats.poisson.ppf(1 - a / 2, e) / e
            rows.append(row)
    return pd.DataFrame(rows)


def rating_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Spearman correlation between CMS star rating and hospital mean ERR."""
    h = (df.dropna(subset=["excess_readmission_ratio", "hospital_overall_rating"])
           .groupby(["facility_id", "state", "hospital_overall_rating"], as_index=False)
           ["excess_readmission_ratio"].mean())
    out = []
    for scope, g in [("Washington", h[h.state == "WA"]), ("United States", h)]:
        if len(g) >= 5:
            r = stats.spearmanr(g["hospital_overall_rating"], g["excess_readmission_ratio"])
            out.append({"scope": scope, "hospitals": len(g), "spearman_rho": r.statistic,
                        "p_value": r.pvalue})
    return pd.DataFrame(out)


def forest_plot(comp: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(comp))
    ax.errorbar(comp.other_states_mean_err, y + 0.15,
                xerr=[comp.other_states_mean_err - comp.other_ci_low,
                      comp.other_ci_high - comp.other_states_mean_err],
                fmt="o", color="#9aa5b1", label="Other states", capsize=3)
    ax.errorbar(comp.wa_mean_err, y - 0.15,
                xerr=[comp.wa_mean_err - comp.wa_ci_low, comp.wa_ci_high - comp.wa_mean_err],
                fmt="o", color="#1f4e79", label="Washington", capsize=3)
    ax.axvline(1, color="#c0392b", lw=1, ls="--")
    ax.set_yticks(y, comp.measure_label)
    ax.set_xlabel("Mean excess readmission ratio (95% CI)   < 1 = fewer readmissions than expected")
    ax.set_title("Washington vs. other states: 30-day readmissions by condition")
    ax.legend(loc="upper left", frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "wa_vs_us_forest.png", dpi=200)
    plt.close(fig)


def funnel_plot(flags: pd.DataFrame, limits: pd.DataFrame, measure: str) -> None:
    g, lim = flags[flags.measure_label == measure], limits[limits.measure_label == measure]
    if g.empty:
        return
    colors = {"Higher than expected": "#c0392b", "Lower than expected": "#1e8449",
              "As expected": "#1f4e79"}
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for lvl, ls in [("95", "--"), ("998", ":")]:
        ax.plot(lim.expected_readmissions, lim[f"upper_{lvl}"], color="grey", ls=ls, lw=1)
        ax.plot(lim.expected_readmissions, lim[f"lower_{lvl}"], color="grey", ls=ls, lw=1)
    ax.axhline(1, color="black", lw=0.8)
    for flag, sub in g.groupby("oe_flag"):
        ax.scatter(sub.expected_readmissions, sub.oe_ratio, s=28, color=colors[flag], label=flag)
    ax.plot([], [], color="grey", ls="--", lw=1, label="95% limits")
    ax.plot([], [], color="grey", ls=":", lw=1, label="99.8% limits")
    ax.set_xlabel("Expected readmissions (hospital volume)")
    ax.set_ylabel("Observed / expected readmissions")
    ax.set_title(f"Washington hospitals: {measure} readmissions funnel plot")
    ax.legend(frameon=False, fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / f"funnel_{measure.lower().replace(' ', '_')}.png", dpi=200)
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql("SELECT * FROM v_readmission_detail", con)
    wa = df[df.state == "WA"]

    comp = state_comparison(df)
    flags = hospital_flags(wa)
    limits = funnel_limits(flags)
    corr = rating_correlation(df)

    comp.round(4).to_csv(PROCESSED / "wa_vs_us_tests.csv", index=False)
    flags.round(4).to_csv(PROCESSED / "wa_hospital_oe_flags.csv", index=False)
    limits.round(4).to_csv(PROCESSED / "funnel_limits.csv", index=False)
    corr.round(4).to_csv(PROCESSED / "rating_correlation.csv", index=False)

    forest_plot(comp)
    funnel_plot(flags, limits, "Heart failure")

    pd.set_option("display.width", 160)
    print(comp[["measure_label", "wa_hospitals", "wa_mean_err", "other_states_mean_err",
                "difference", "p_welch_bh", "significant_fdr_05"]].round(3).to_string(index=False))
    print()
    print(flags["oe_flag"].value_counts().to_string())
    print()
    print(corr.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
