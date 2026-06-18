"""Step 4 — Train the three target models (+ honest variants) on a chronological split.

  T1 closure   : XGBClassifier + scale_pos_weight, then isotonic-calibrated probabilities
                 and an F1-optimal threshold chosen on the validation PR curve.
  T2 priority  : XGBClassifier (full) + a corridor-blind variant (the priority rule is
                 ~100% corridor-determined; the blind model tests recoverability).
  T3 duration  : XGBoost survival:aft — uses the 1,007 right-censored 'active' incidents
                 as [elapsed, +inf]; plus a log1p XGBRegressor baseline for comparison.
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from xgboost import XGBClassifier, XGBRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import precision_recall_curve
from sklearn.utils.class_weight import compute_sample_weight

from . import config as C
from .prepare import prepare, split_xy


def _best_f1_threshold(y, p):
    prec, rec, thr = precision_recall_curve(y, p)
    f1 = 2 * prec * rec / (prec + rec + 1e-9)
    return float(thr[max(0, np.argmax(f1[:-1]))])


def recall_at(y, p, cut):
    yh = (p >= cut).astype(int)
    tp = ((yh == 1) & (y == 1)).sum()
    return tp / max(1, (y == 1).sum())


def train_t1(prep):
    Xtr, ytr, Xva, yva, Xte, yte, feats = split_xy(prep, C.T1)
    ytr, yva = ytr.astype(int), yva.astype(int)
    spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
    model = XGBClassifier(**C.XGB_CLF_PARAMS, scale_pos_weight=spw, early_stopping_rounds=50)
    model.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    raw_va = model.predict_proba(Xva)[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip").fit(raw_va, yva)
    cal_va = iso.predict(raw_va)
    thr = _best_f1_threshold(yva, cal_va)
    # high-recall alert threshold: lowest cutoff that catches >=60% of closures on val
    # (missing a real closure is operationally costly, so dispatch may prefer this point).
    order = np.argsort(cal_va)
    rec_thr = thr
    for cut in np.linspace(0.02, 0.6, 60):
        if recall_at(yva, cal_va, cut) >= 0.60:
            rec_thr = float(cut)
    print(f"T1: scale_pos_weight={spw:.1f}, f1_threshold={thr:.3f}, "
          f"recall_threshold={rec_thr:.3f}, features={len(feats)}")
    return {"model": model, "isotonic": iso, "threshold": thr,
            "recall_threshold": rec_thr, "features": feats}


def train_t2(prep):
    out = {}
    for blind, key in [(False, "full"), (True, "corridor_blind")]:
        Xtr, ytr, Xva, yva, Xte, yte, feats = split_xy(prep, C.T2, corridor_blind=blind)
        ytr, yva = ytr.astype(int), yva.astype(int)
        spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
        m = XGBClassifier(**C.XGB_CLF_PARAMS, scale_pos_weight=spw, early_stopping_rounds=50)
        m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        out[key] = {"model": m, "features": feats}
    print(f"T2: trained full ({len(out['full']['features'])} feats) + "
          f"corridor-blind ({len(out['corridor_blind']['features'])} feats)")
    return out


def train_t3(prep):
    df = prep.df
    feats = C.get_feature_columns(df)

    def slice_split(sp):
        s = df[(df["split"] == sp) & (df[C.T3].notna())]
        X = s[feats].astype(float)
        lower = s[C.T3].to_numpy(dtype=float)
        upper = np.where(s["is_censored"].to_numpy() == 1, np.inf, lower)
        return s, X, lower, upper

    s_tr, Xtr, lo_tr, up_tr = slice_split("train")
    s_va, Xva, lo_va, up_va = slice_split("val")

    # ---- AFT survival model (handles right-censored active incidents)
    dtr = xgb.DMatrix(Xtr); dtr.set_float_info("label_lower_bound", lo_tr)
    dtr.set_float_info("label_upper_bound", up_tr)
    dva = xgb.DMatrix(Xva); dva.set_float_info("label_lower_bound", lo_va)
    dva.set_float_info("label_upper_bound", up_va)
    aft = xgb.train(C.XGB_AFT_PARAMS, dtr, num_boost_round=C.AFT_NUM_BOOST_ROUND,
                    evals=[(dtr, "train"), (dva, "val")], early_stopping_rounds=40,
                    verbose_eval=False)
    n_cens_tr = int((s_tr["is_censored"] == 1).sum())
    print(f"T3 AFT: trained on {len(s_tr)} rows ({n_cens_tr} right-censored), "
          f"best_iter={aft.best_iteration}")

    # ---- log1p operational regressor (uncensored, target capped at 6h -> actionable range)
    unc = s_tr[s_tr["is_censored"] == 0]
    cap = float(C.T3_REG_CAP_MIN)
    ytr_log = np.log1p(np.minimum(unc[C.T3].to_numpy(), cap))
    unc_va = s_va[s_va["is_censored"] == 0]
    yva_log = np.log1p(np.minimum(unc_va[C.T3].to_numpy(), cap))
    reg = XGBRegressor(**C.XGB_REG_PARAMS, early_stopping_rounds=50)
    reg.fit(unc[feats].astype(float), ytr_log,
            eval_set=[(unc_va[feats].astype(float), yva_log)], verbose=False)
    global_median = float(unc[C.T3].median())
    print(f"T3 log1p operational: trained on {len(unc)} uncensored rows, cap={cap:.0f} min, "
          f"global_median={global_median:.0f} min")
    return {"aft": aft, "aft_best_iter": aft.best_iteration, "log_reg": reg,
            "log_cap": cap, "global_median": global_median, "features": feats,
            "bucket": train_t3_bucket(prep, feats)}


def train_t3_bucket(prep, feats):
    """4-class duration bucket classifier on uncensored rows only."""
    df = prep.df
    tv = df[df["split"].isin(["train", "val"]) & (df["is_censored"] == 0) & df[C.T3].notna()].copy()
    tv["_bkt"] = pd.cut(tv[C.T3], bins=C.DURATION_BUCKET_BINS,
                        labels=[0, 1, 2, 3], right=True).astype(int)
    tr = tv[tv["split"] == "train"]
    va = tv[tv["split"] == "val"]
    sw = compute_sample_weight("balanced", tr["_bkt"])
    params = {k: v for k, v in C.XGB_CLF_PARAMS.items()
              if k not in ("eval_metric",)}
    clf = XGBClassifier(**params, objective="multi:softmax", num_class=4,
                        eval_metric="mlogloss", early_stopping_rounds=40)
    clf.fit(tr[feats].astype(float), tr["_bkt"], sample_weight=sw,
            eval_set=[(va[feats].astype(float), va["_bkt"])], verbose=False)
    dist = tr["_bkt"].value_counts().sort_index().to_dict()
    print(f"T3 bucket: {len(tr)} train rows | class dist: {dist}")
    return {"model": clf, "features": feats,
            "bins": C.DURATION_BUCKET_BINS, "labels": C.DURATION_BUCKET_LABELS}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    prep = prepare()
    print(f"prepared: {len(prep.df)} rows | "
          f"split counts: {prep.df['split'].value_counts().to_dict()}")

    t1 = train_t1(prep)
    t2 = train_t2(prep)
    t3 = train_t3(prep)

    joblib.dump(t1, C.MODELS_DIR / "t1_closure.joblib")
    joblib.dump(t2, C.MODELS_DIR / "t2_priority.joblib")
    joblib.dump(t3, C.MODELS_DIR / "t3_duration.joblib")
    joblib.dump(prep.context, C.MODELS_DIR / "context.joblib")

    # leakage guard on the persisted feature lists
    for name, feats in [("t1", t1["features"]), ("t2", t2["full"]["features"]),
                        ("t3", t3["features"])]:
        bad = [c for c in feats if c in C.BANNED_LEAKAGE]
        assert not bad, f"LEAKAGE in {name}: {bad}"
    print("\nOK: models trained, persisted, no banned leakage in feature lists.")


if __name__ == "__main__":
    main()
