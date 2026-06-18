"""Step 0 — Comprehensive EDA figure generators (used by notebooks/01_eda.ipynb + report).

`generate_all()` writes every figure into reports/figures/eda/ and a findings markdown.
All analysis is on the provided dataset only.
"""
from __future__ import annotations
import os
os.environ.setdefault("PYTHONBREAKPOINT", "0")
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import config as C

EDA_DIR = C.FIGURES_DIR / "eda"
EDA_DIR.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, RED = "#2b8cbe", "#e6550d", "#a50f15"


def _save(fig, name):
    fig.tight_layout(); fig.savefig(EDA_DIR / name, dpi=110, bbox_inches="tight")
    plt.close(fig); return EDA_DIR / name


def load():
    raw = pd.read_csv(C.RAW_CSV, low_memory=False)
    df = pd.read_parquet(C.CLEAN_PARQUET)
    df["rc"] = df[C.T1].astype(float)
    df["hour"] = df["start_ist"].dt.hour
    df["month"] = df["start_ist"].dt.to_period("M").astype(str)
    return raw, df


def fig_null_rates(raw):
    nr = (raw.isna().mean() * 100).sort_values(ascending=False).head(24)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(nr.index[::-1], nr.values[::-1], color=BLUE)
    ax.set_xlabel("% missing"); ax.set_title("Missingness by column (raw dataset)")
    ax.axvline(99.9, color=RED, ls="--", lw=1, label="dropped (≈100% null)")
    ax.legend()
    return _save(fig, "01_null_rates.png")


def fig_targets(df):
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    df[C.T1].value_counts().sort_index().plot.bar(ax=ax[0], color=[BLUE, RED])
    ax[0].set_title(f"T1 requires_road_closure\n({df[C.T1].mean()*100:.1f}% positive — imbalanced)")
    ax[0].set_xticklabels(["No", "Yes"], rotation=0)
    df[C.T2].value_counts().sort_index().plot.bar(ax=ax[1], color=[BLUE, ORANGE])
    ax[1].set_title(f"T2 priority\n({df[C.T2].mean()*100:.1f}% High)")
    ax[1].set_xticklabels(["Low", "High"], rotation=0)
    unc = df.loc[df["is_censored"] == 0, C.T3]
    ax[2].hist(np.log1p(unc.clip(upper=unc.quantile(0.99))), bins=40, color=BLUE)
    ax[2].set_title("T3 resolution time (log1p minutes)\nheavy-tailed")
    ax[2].set_xlabel("log1p(minutes)")
    return _save(fig, "02_target_distributions.png")


def fig_breakdown_spike(df):
    vb = df[(df["event_cause_norm"] == "vehicle_breakdown") & (df["is_censored"] == 0)]
    res = (df["modified_datetime"] - df["start_datetime"]).dt.total_seconds() / 60
    vb_res = res[vb.index]
    vb_res = vb_res[(vb_res > 0) & (vb_res < 400)]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(vb_res, bins=60, color=ORANGE)
    ax.axvspan(120, 180, color=RED, alpha=0.15, label="120–180 min (61% of breakdowns)")
    ax.set_title("Recording artifact: vehicle-breakdown 'resolution' clusters ~135 min")
    ax.set_xlabel("modified − start (minutes)"); ax.legend()
    return _save(fig, "03_breakdown_artifact.png")


def fig_closure_drivers(df):
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    cr = df.groupby("event_cause_norm")["rc"].mean().sort_values(ascending=False).head(14)
    ax[0].barh(cr.index[::-1], cr.values[::-1], color=BLUE)
    ax[0].set_title("Closure rate by event cause (event-driven causes dominate)")
    ax[0].set_xlabel("P(road closure)")
    pv = df.groupby("event_type")["rc"].mean()
    ax[1].bar(pv.index, pv.values, color=[BLUE, RED])
    ax[1].set_title("Closure rate: planned vs unplanned (5×)")
    ax[1].set_ylabel("P(road closure)")
    return _save(fig, "04_closure_drivers.png")


def fig_temporal(df):
    fig, ax = plt.subplots(1, 2, figsize=(14, 4))
    h = df.groupby("hour")["rc"].mean()
    ax[0].bar(h.index, h.values, color=BLUE)
    for x in [11, 12, 16, 17, 18, 19]:
        ax[0].axvspan(x - 0.5, x + 0.5, color=RED, alpha=0.12)
    ax[0].set_title("Closure rate by hour (IST) — midday + evening spikes")
    ax[0].set_xlabel("hour")
    mo = df.groupby("month")["rc"].mean()
    ax[1].plot(mo.index, mo.values, "o-", color=ORANGE)
    ax[1].set_title("Closure rate trend by month"); ax[1].tick_params(axis="x", rotation=45)
    return _save(fig, "05_temporal.png")


def fig_spatial(df):
    fig, ax = plt.subplots(figsize=(7, 6))
    sc = ax.scatter(df["longitude"], df["latitude"], c=df["rc"], cmap="coolwarm",
                    s=6, alpha=0.5)
    ax.set_title("Incidents across Bengaluru (red = road closure)")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    plt.colorbar(sc, ax=ax, label="closure")
    return _save(fig, "06_spatial.png")


def fig_leakage_audit(df):
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
    # (a) end-point leakage
    has_end = (df["endlatitude"].fillna(0) != 0).astype(int)
    ct = pd.crosstab(has_end, df[C.T1])
    ct.plot.bar(stacked=True, ax=ax[0], color=[BLUE, RED])
    ax[0].set_title("LEAK: end-point present ⇒ closure (98%)")
    ax[0].set_xticklabels(["no end point", "has end point"], rotation=0)
    ax[0].set_xlabel(""); ax[0].legend(["no closure", "closure"])
    # (b) priority determinism
    hr = df.groupby("corridor")[C.T2].mean().sort_values()
    ax[1].bar(range(len(hr)), hr.values, color=ORANGE)
    ax[1].set_title("T2 determinism: corridor → priority (0 or 1)")
    ax[1].set_xlabel("corridors (sorted)"); ax[1].set_ylabel("% High priority")
    # (c) resolution flat by priority/closure but huge by cause
    res = (df["modified_datetime"] - df["start_datetime"]).dt.total_seconds() / 60
    sub = df[(df["is_censored"] == 0)].copy(); sub["res"] = res[sub.index]
    sub = sub[sub["res"] > 0]
    med = sub.groupby("event_cause_norm")["res"].median().sort_values(ascending=False).head(10)
    ax[2].barh(med.index[::-1], med.values[::-1], color=BLUE)
    ax[2].set_xscale("log")
    ax[2].set_title("Resolution median by cause (log) — 500× spread")
    ax[2].set_xlabel("minutes (log)")
    return _save(fig, "07_leakage_determinism_audit.png")


def fig_text(df):
    import re
    from collections import Counter
    d = df["description"].dropna().astype(str)
    ascii_share = d.apply(lambda s: s.isascii()).mean()
    toks = Counter()
    for s in d[d.apply(lambda x: x.isascii())].str.lower():
        for w in re.findall(r"[a-z]{4,}", s):
            toks[w] += 1
    stop = set("with this that have from your sir near road work been will".split())
    common = [(w, c) for w, c in toks.most_common(40) if w not in stop][:18]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh([w for w, _ in common][::-1], [c for _, c in common][::-1], color=BLUE)
    ax.set_title(f"Description keywords ({df['description'].notna().mean()*100:.0f}% coverage, "
                 f"{ascii_share*100:.0f}% English/Kanglish, rest Kannada)")
    return _save(fig, "08_text_keywords.png")


def generate_all():
    raw, df = load()
    paths = [fig_null_rates(raw), fig_targets(df), fig_breakdown_spike(df),
             fig_closure_drivers(df), fig_temporal(df), fig_spatial(df),
             fig_leakage_audit(df), fig_text(df)]
    findings = (
        f"# EDA findings\n\n"
        f"- Rows: {len(df)} | period {df['start_datetime'].min().date()} → "
        f"{df['start_datetime'].max().date()}\n"
        f"- T1 closure: {df[C.T1].mean()*100:.1f}% positive (imbalanced)\n"
        f"- T2 priority: {df[C.T2].mean()*100:.1f}% High; deterministic from corridor\n"
        f"- Planned events: {(df['event_type']=='planned').sum()} "
        f"(closure {df.loc[df['event_type']=='planned','rc'].mean()*100:.0f}% vs "
        f"unplanned {df.loc[df['event_type']=='unplanned','rc'].mean()*100:.0f}%)\n"
        f"- End-point leakage, priority determinism, and the breakdown artifact are the three "
        f"headline data findings.\n"
    )
    (C.REPORTS_DIR / "EDA_FINDINGS.md").write_text(findings, encoding="utf-8")
    return [str(p) for p in paths]


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    for p in generate_all():
        print("saved", p)
