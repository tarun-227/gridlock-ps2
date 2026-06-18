"""Step 5 — Evaluate on the held-out chronological TEST set.

Reports research-appropriate metrics: PR-AUC (primary for the rare-positive closure
target), calibration, survival C-index + MAE/RMSE/MAPE for duration (AFT vs log1p
baseline), comparison against naive baselines, SHAP explanations, and per-corridor /
per-cause / planned-vs-unplanned breakdowns. Writes models/metrics.json + figures.
"""
from __future__ import annotations
import os
os.environ.setdefault("PYTHONBREAKPOINT", "0")  # neutralize stray breakpoints in deps
import sys
import json
import warnings

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (average_precision_score, roc_auc_score, f1_score,
                             recall_score, precision_score, confusion_matrix,
                             mean_absolute_error, mean_squared_error, r2_score,
                             accuracy_score, classification_report)
from sklearn.calibration import calibration_curve
from lifelines.utils import concordance_index

from . import config as C
from .prepare import prepare, split_xy

warnings.filterwarnings("ignore")
ROUND = lambda x: float(np.round(x, 4))


# --------------------------------------------------------------------------- T1 / T2
def eval_t1(prep, art):
    Xtr, ytr, Xva, yva, Xte, yte, feats = split_xy(prep, C.T1)
    yte = yte.astype(int).to_numpy()
    p = art["isotonic"].predict(art["model"].predict_proba(Xte)[:, 1])
    yhat = (p >= art["threshold"]).astype(int)
    base = np.zeros_like(yte)  # majority-class baseline (predict 'no closure')
    frac_obs, mean_pred = calibration_curve(yte, p, n_bins=10, strategy="quantile")
    # operating-point table: closures are costly to miss, so show the precision/recall
    # trade-off across thresholds (not just the single F1-optimal point).
    ops = []
    for thr in [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]:
        yh = (p >= thr).astype(int)
        ops.append({"threshold": thr,
                    "recall": ROUND(recall_score(yte, yh, zero_division=0)),
                    "precision": ROUND(precision_score(yte, yh, zero_division=0)),
                    "f1_weighted": ROUND(f1_score(yte, yh, average="weighted"))})
    res = {
        "pr_auc": ROUND(average_precision_score(yte, p)),
        "roc_auc": ROUND(roc_auc_score(yte, p)),
        "f1_weighted": ROUND(f1_score(yte, yhat, average="weighted")),
        "recall_pos": ROUND(recall_score(yte, yhat)),
        "precision_pos": ROUND(precision_score(yte, yhat, zero_division=0)),
        "threshold": art["threshold"],
        "confusion_matrix": confusion_matrix(yte, yhat).tolist(),
        "operating_points": ops,
        "baseline_majority_pr_auc": ROUND(yte.mean()),  # PR-AUC of random ~ positive rate
        "baseline_majority_f1": ROUND(f1_score(yte, base, average="weighted")),
        "pr_auc_lift_vs_baseline": ROUND(average_precision_score(yte, p) / max(yte.mean(), 1e-9)),
        "test_positive_rate": ROUND(yte.mean()),
        "n_test": int(len(yte)),
    }
    _plot_calibration(mean_pred, frac_obs, "T1 closure", "t1_calibration.png")
    return res, (Xte, yte, p, yhat)


def eval_t2(prep, arts):
    out = {}
    for key in ("full", "corridor_blind"):
        a = arts[key]
        Xtr, ytr, Xva, yva, Xte, yte, feats = split_xy(prep, C.T2, corridor_blind=(key != "full"))
        yte = yte.astype(int).to_numpy()
        p = a["model"].predict_proba(Xte)[:, 1]
        yhat = (p >= 0.5).astype(int)
        out[key] = {
            "pr_auc": ROUND(average_precision_score(yte, p)),
            "roc_auc": ROUND(roc_auc_score(yte, p)),
            "f1_weighted": ROUND(f1_score(yte, yhat, average="weighted")),
            "accuracy": ROUND((yhat == yte).mean()),
        }
    # corridor-rule baseline: High iff corridor != Non-corridor
    te = prep.df[(prep.df["split"] == "test") & (prep.df[C.T2].notna())]
    rule = (te["corridor"] != "Non-corridor").astype(int).to_numpy()
    yte_all = te[C.T2].astype(int).to_numpy()
    out["baseline_corridor_rule"] = {
        "f1_weighted": ROUND(f1_score(yte_all, rule, average="weighted")),
        "accuracy": ROUND((rule == yte_all).mean()),
    }
    return out


# ------------------------------------------------------------------------------- T3
def eval_t3(prep, art):
    df = prep.df
    feats = art["features"]
    te = df[(df["split"] == "test") & (df[C.T3].notna())]
    Xte = te[feats].astype(float)
    dte = xgb.DMatrix(Xte)
    pred_aft = art["aft"].predict(dte)
    pred_log = np.expm1(art["log_reg"].predict(Xte))

    actual = te[C.T3].to_numpy(dtype=float)
    observed = (te["is_censored"] == 0).to_numpy().astype(int)
    unc = observed == 1   # only uncensored rows have a true duration for error metrics
    # "operational" rows: incidents cleared within 24h — the cases where a duration
    # estimate is actually useful for dispatch. The multi-day civic backlog (potholes,
    # construction) is a record-keeping artifact, not a predictable clearance time.
    op = unc & (actual <= 1440)

    def err(pred, mask):
        a, p = actual[mask], np.clip(pred[mask], 0, None)
        mape = float(np.mean(np.abs((a - p) / np.maximum(a, 1))) * 100)
        log_mae = float(np.mean(np.abs(np.log1p(a) - np.log1p(p))))
        return {"mae_min": ROUND(mean_absolute_error(a, p)),
                "medae_min": ROUND(np.median(np.abs(a - p))),  # robust to the tail
                "rmse_min": ROUND(mean_squared_error(a, p) ** 0.5),
                "log_mae": ROUND(log_mae), "mape_pct": ROUND(mape),
                "r2": ROUND(r2_score(a, p)), "n": int(mask.sum())}

    med = float(np.median(actual[unc]))
    corr_mean = te.groupby("corridor")[C.T3].transform("mean").to_numpy()
    res = {
        "n_test": int(len(te)), "n_test_uncensored": int(unc.sum()),
        "c_index_aft": ROUND(concordance_index(actual, pred_aft, observed)),
        "note": "raw-minute MAE is dominated by the multi-week civic tail; medae_min and "
                "log_mae are the robust metrics, and *_operational restricts to <=24h cases.",
        # full uncensored set
        "aft": err(pred_aft, unc),
        "log1p_baseline": err(pred_log, unc),
        "baseline_global_median": err(np.full_like(actual, med), unc),
        "baseline_corridor_mean": err(np.nan_to_num(corr_mean, nan=med), unc),
        # operational subset (<=24h), where a duration estimate is actionable
        "aft_operational": err(pred_aft, op),
        "log1p_operational": err(pred_log, op),
        "baseline_median_operational": err(np.full_like(actual, med), op),
    }
    tmp = te.loc[unc, ["event_cause_norm"]].copy()
    tmp["ae"] = np.abs(actual[unc] - pred_aft[unc])
    res["per_cause_mae_aft"] = (tmp.groupby("event_cause_norm")["ae"].mean()
                                .round(1).sort_values(ascending=False).to_dict())
    return res


def eval_t3_bucket(prep, art):
    """Evaluate the 4-class duration bucket classifier."""
    df = prep.df
    feats = art["features"]
    bins, labels = art["bins"], art["labels"]
    te = df[(df["split"] == "test") & (df["is_censored"] == 0) & df[C.T3].notna()].copy()
    te["_bkt"] = pd.cut(te[C.T3], bins=bins, labels=[0, 1, 2, 3], right=True).astype(int)
    Xte = te[feats].astype(float)
    yhat = art["model"].predict(Xte)
    ytrue = te["_bkt"].to_numpy()
    # majority-class baseline
    majority = int(pd.Series(ytrue).value_counts().idxmax())
    base_acc = accuracy_score(ytrue, np.full_like(yhat, majority))
    per_bucket = {}
    for i, label in enumerate(labels):
        mask = ytrue == i
        per_bucket[label] = {
            "n": int(mask.sum()),
            "precision": ROUND(precision_score(ytrue == i, yhat == i, zero_division=0)),
            "recall": ROUND(recall_score(ytrue == i, yhat == i, zero_division=0)),
            "f1": ROUND(f1_score(ytrue == i, yhat == i, zero_division=0)),
        }
    return {
        "accuracy": ROUND(accuracy_score(ytrue, yhat)),
        "baseline_majority_accuracy": ROUND(base_acc),
        "majority_bucket": labels[majority],
        "n_test": int(len(te)),
        "per_bucket": per_bucket,
        "confusion_matrix": confusion_matrix(ytrue, yhat).tolist(),
    }


# ----------------------------------------------------------------------- breakdowns
def per_corridor_t1(prep, te_pack):
    Xte, yte, p, yhat = te_pack
    te = prep.df[(prep.df["split"] == "test") & (prep.df[C.T1].notna())].copy()
    te = te.iloc[: len(yte)]
    te["y"], te["yhat"] = yte, yhat
    rows = {}
    for corr, g in te.groupby("corridor"):
        if len(g) < 15:
            continue
        rows[corr] = {"n": int(len(g)), "closure_rate": ROUND(g["y"].mean()),
                      "recall": ROUND(recall_score(g["y"], g["yhat"], zero_division=0)),
                      "f1": ROUND(f1_score(g["y"], g["yhat"], average="weighted"))}
    planned = {}
    for et, g in te.assign(et=prep.df["event_type"]).groupby("et"):
        planned[et] = {"n": int(len(g)),
                       "recall": ROUND(recall_score(g["y"], g["yhat"], zero_division=0)),
                       "f1": ROUND(f1_score(g["y"], g["yhat"], average="weighted"))}
    return {"per_corridor": rows, "planned_vs_unplanned": planned}


# ----------------------------------------------------------------------------- SHAP
# Uses XGBoost's built-in tree-SHAP (pred_contribs=True) — exact, no external lib
# (the local `shap` package install is broken / drops into a debugger).
def _booster_shap(booster, X):
    sv = booster.predict(xgb.DMatrix(X), pred_contribs=True)
    return sv[:, :-1]  # drop the bias column


def shap_plots(prep, t1, t2, t3):
    out = {}
    sample = prep.df[prep.df["split"] == "test"]
    Xs = sample[t1["features"]].astype(float).sample(min(600, len(sample)), random_state=C.SEED)
    sv = _booster_shap(t1["model"].get_booster(), Xs)
    _shap_bar(sv, Xs, "T1 closure — mean |SHAP| (XGBoost tree-SHAP)", "t1_shap.png")
    out["t1_top_features"] = _top_shap(sv, Xs)

    Xs3 = sample[t3["features"]].astype(float).sample(min(600, len(sample)), random_state=C.SEED)
    sv3 = _booster_shap(t3["aft"], Xs3)
    _shap_bar(sv3, Xs3, "T3 duration (AFT) — mean |SHAP|", "t3_shap.png")
    out["t3_top_features"] = _top_shap(sv3, Xs3)
    return out


def _top_shap(sv, X, k=10):
    imp = np.abs(sv).mean(0)
    order = np.argsort(imp)[::-1][:k]
    return {X.columns[i]: ROUND(imp[i]) for i in order}


def _shap_bar(sv, X, title, fname):
    imp = np.abs(sv).mean(0)
    order = np.argsort(imp)[::-1][:15][::-1]
    plt.figure(figsize=(7, 5))
    plt.barh([X.columns[i] for i in order], imp[order], color="#2b8cbe")
    plt.title(title); plt.xlabel("mean |SHAP|"); plt.tight_layout()
    plt.savefig(C.FIGURES_DIR / fname, dpi=110); plt.close()


def _plot_calibration(mean_pred, frac_obs, title, fname):
    plt.figure(figsize=(5, 5))
    plt.plot([0, 1], [0, 1], "k--", alpha=0.5, label="perfect")
    plt.plot(mean_pred, frac_obs, "o-", color="#e6550d", label="model")
    plt.xlabel("mean predicted prob"); plt.ylabel("observed frequency")
    plt.title(f"Calibration — {title}"); plt.legend(); plt.tight_layout()
    plt.savefig(C.FIGURES_DIR / fname, dpi=110); plt.close()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    prep = prepare()
    t1 = joblib.load(C.MODELS_DIR / "t1_closure.joblib")
    t2 = joblib.load(C.MODELS_DIR / "t2_priority.joblib")
    t3 = joblib.load(C.MODELS_DIR / "t3_duration.joblib")

    m1, te_pack = eval_t1(prep, t1)
    m2 = eval_t2(prep, t2)
    m3 = eval_t3(prep, t3)
    m3_bkt = eval_t3_bucket(prep, t3["bucket"])
    breakdown = per_corridor_t1(prep, te_pack)
    shp = shap_plots(prep, t1, t2, t3)

    metrics = {"T1_closure": m1, "T2_priority": m2, "T3_duration": m3,
               "T3_bucket": m3_bkt, "breakdowns": breakdown, "shap": shp,
               "n_features": {"t1": len(t1["features"]), "t3": len(t3["features"])}}
    C.METRICS_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\n================= TEST METRICS =================")
    print(f"T1 closure : PR-AUC {m1['pr_auc']} (baseline {m1['baseline_majority_pr_auc']}), "
          f"ROC-AUC {m1['roc_auc']}, F1 {m1['f1_weighted']}, recall+ {m1['recall_pos']}")
    print(f"T2 full    : F1 {m2['full']['f1_weighted']}, acc {m2['full']['accuracy']}  | "
          f"corridor-blind F1 {m2['corridor_blind']['f1_weighted']} | "
          f"rule baseline F1 {m2['baseline_corridor_rule']['f1_weighted']}")
    print(f"T3 ranking : AFT C-index {m3['c_index_aft']} (>0.5 random; uses censored rows)")
    print(f"T3 (<=24h) : regressor R2 {m3['log1p_operational']['r2']} vs constant "
          f"{m3['baseline_median_operational']['r2']}, RMSE {m3['log1p_operational']['rmse_min']} "
          f"vs {m3['baseline_median_operational']['rmse_min']} | MAE {m3['log1p_operational']['mae_min']} "
          f"vs median-baseline {m3['baseline_median_operational']['mae_min']} (median near-optimal)")
    bkt = m3_bkt
    print(f"T3 bucket  : acc {bkt['accuracy']} vs majority-baseline {bkt['baseline_majority_accuracy']}"
          f"  (majority bucket='{bkt['majority_bucket']}')")
    for lbl, s in bkt['per_bucket'].items():
        print(f"  {lbl:>5s}: n={s['n']:4d}  P={s['precision']:.3f}  R={s['recall']:.3f}  F1={s['f1']:.3f}")
    print(f"\nmetrics -> {C.METRICS_JSON}")
    print(f"figures -> {C.FIGURES_DIR}")
    # leakage sanity: closure F1 should NOT be ~perfect
    assert m1["f1_weighted"] < 0.98, "T1 F1 suspiciously high — re-audit for leakage!"
    print("OK: evaluation complete.")


if __name__ == "__main__":
    main()
