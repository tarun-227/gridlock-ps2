"""Single-incident inference: featurize a new report -> T1/T2/T3 -> recommendation.

Used by the dashboard. Recurrence/spatial features for a hypothetical new incident are
filled from the train-derived context (per-corridor closure rates, city load, median
feature template), so the same model that was trained offline can score a live report.
"""
from __future__ import annotations
import functools
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb

from . import config as C
from . import llm_extract
from .text_features import rule_extract
from .recommend import recommend


@functools.lru_cache(maxsize=1)
def load_artifacts():
    return {
        "t1": joblib.load(C.MODELS_DIR / "t1_closure.joblib"),
        "t2": joblib.load(C.MODELS_DIR / "t2_priority.joblib"),
        "t3": joblib.load(C.MODELS_DIR / "t3_duration.joblib"),
        "context": joblib.load(C.MODELS_DIR / "context.joblib"),
    }


def _enc(context, col, val):
    return context["encoders"].get(col, {}).get(str(val), -1)


def _hour_bucket(h):
    return 0 if h <= 5 else 1 if h <= 11 else 2 if h <= 16 else 3 if h <= 20 else 4


def extract_description(desc, live_llm=False):
    """LLM cache -> live LLM (optional) -> rule-based fallback."""
    if not desc or not str(desc).strip():
        from .text_features import DEFAULTS
        return dict(DEFAULTS)
    cache = llm_extract.load_cache()
    h = llm_extract._hash(str(desc).strip())
    if h in cache:
        return cache[h]
    if live_llm:
        try:
            return llm_extract.extract_one(str(desc))   # Groq if key set, else Ollama
        except Exception:
            pass
    return rule_extract(str(desc))


def featurize_one(record: dict, context: dict, feature_list, live_llm=False) -> pd.DataFrame:
    row = dict(context["feature_medians"])  # robust defaults
    dt = record.get("datetime") or datetime.now()
    h = dt.hour
    row.update({
        "hour": h, "day_of_week": dt.weekday(), "is_weekend": int(dt.weekday() >= 5),
        "month_of_year": dt.month, "is_peak": int(h in (11, 12, 16, 17, 18, 19)),
        "is_night": int(h <= 5), "hour_bucket": _hour_bucket(h),
    })

    corridor = record.get("corridor", "Non-corridor")
    cs = context["corridor_stats"].get(corridor, {})
    row.update({
        "corridor_le": _enc(context, "corridor", corridor),
        "is_non_corridor": int(corridor == "Non-corridor"),
        "corridor_closure_rate": cs.get("corridor_closure_rate", context["base_closure_rate"]),
        "corridor_high_rate": cs.get("corridor_high_rate", context["base_high_rate"]),
        "corridor_inc_7d": cs.get("corridor_inc_7d", 0.0),
        "corridor_inc_30d": cs.get("corridor_inc_30d", 0.0),
        "corridor_days_since_last": cs.get("corridor_days_since_last", 30.0),
    })

    zone = record.get("zone")
    row.update({
        "zone_le": _enc(context, "zone", zone),
        "zone_closure_rate": context["zone_closure_rate"].get(zone, context["base_closure_rate"]),
        "zone_missing": int(zone is None or str(zone) == "nan" or zone == ""),
    })

    veh = record.get("veh_type")
    row["veh_type_le"] = _enc(context, "veh_type", veh)
    row["is_heavy_vehicle"] = int(veh in {"heavy_vehicle", "truck", "lcv", "tanker", "container"})
    row["event_cause_norm_le"] = _enc(context, "event_cause_norm", record.get("event_cause"))
    row["police_station_le"] = _enc(context, "police_station", record.get("police_station"))

    row["is_planned"] = int(record.get("is_planned", False))
    desc = record.get("description", "")
    row["has_description"] = int(bool(desc and str(desc).strip()))
    row["city_inc_1d"] = context.get("city_inc_1d_median", row.get("city_inc_1d", 0))

    cause = record.get("event_cause")
    cause_cr = context.get("cause_closure_rate", {}).get(
        str(cause) if cause else "", context["base_closure_rate"])
    row["cause_closure_rate"] = cause_cr
    row["veh_closure_rate"] = context.get("veh_closure_rate", {}).get(
        str(veh) if veh else "", context["base_closure_rate"])
    ps = record.get("police_station")
    row["police_station_closure_rate"] = context.get("police_station_closure_rate", {}).get(
        str(ps) if ps else "", context["base_closure_rate"])

    is_planned_val = int(record.get("is_planned", False))
    corr_cr = row.get("corridor_closure_rate", context["base_closure_rate"])
    row["planned_cause_risk"] = is_planned_val * cause_cr
    row["peak_cause_risk"] = row.get("is_peak", 0) * cause_cr
    row["corridor_cause_risk"] = corr_cr * cause_cr

    lat, lon = record.get("latitude"), record.get("longitude")
    clat, clon = context["centroid"]
    if lat is not None and lon is not None:
        row["latitude"], row["longitude"] = float(lat), float(lon)
    else:
        row["latitude"], row["longitude"] = clat, clon

    ex = extract_description(desc, live_llm=live_llm)
    row["llm_severity_score"] = ex["severity_score"]
    row["llm_blocking_lanes"] = int(ex["blocking_lanes"])
    row["llm_vehicles_involved"] = ex["vehicles_involved"]
    row["llm_requires_tow"] = int(ex["requires_tow"])
    row["llm_subtype_le"] = _enc(context, "llm_subtype", ex["incident_subtype"])
    row["llm_subtype_closure_rate"] = context.get("llm_subtype_closure_rate", {}).get(
        ex["incident_subtype"], context["base_closure_rate"])

    dur_cache = llm_extract.load_duration_cache()
    h_dur = llm_extract._hash(str(desc).strip()) if desc and str(desc).strip() else ""
    llm_dur = dur_cache.get(h_dur, {}).get("estimated_duration_min", 0)
    cause_dur_mean = context.get("cause_duration_mean", {}).get(
        str(cause) if cause else "", context.get("global_median_res_min", 134))
    row["llm_estimated_duration_min"] = float(llm_dur) if llm_dur else float(cause_dur_mean)

    X = pd.DataFrame([{f: row.get(f, 0.0) for f in feature_list}]).astype(float)
    return X, ex


def top_reasons(model, X, k=5):
    contrib = model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)[0][:-1]
    order = np.argsort(np.abs(contrib))[::-1][:k]
    return [(X.columns[i], float(contrib[i])) for i in order]


def predict_all(record: dict, live_llm=False) -> dict:
    art = load_artifacts()
    ctx = art["context"]
    t1, t2, t3 = art["t1"], art["t2"], art["t3"]

    X1, ex = featurize_one(record, ctx, t1["features"], live_llm=live_llm)
    closure_prob = float(t1["isotonic"].predict(t1["model"].predict_proba(X1)[:, 1])[0])

    X2, _ = featurize_one(record, ctx, t2["full"]["features"], live_llm=live_llm)
    high_prob = float(t2["full"]["model"].predict_proba(X2)[:, 1][0])

    X3, _ = featurize_one(record, ctx, t3["features"], live_llm=live_llm)
    res_min = float(np.clip(np.expm1(t3["log_reg"].predict(X3))[0], 0, None))
    aft_rank = float(t3["aft"].predict(xgb.DMatrix(X3))[0])

    # T3 duration bucket (0=<1h, 1=1-3h, 2=3-8h, 3=>8h)
    bucket_labels = ["<1h", "1-3h", "3-8h", ">8h"]
    bucket_idx = int(t3["bucket"]["model"].predict(X3)[0])
    bucket_idx = max(0, min(3, bucket_idx))
    duration_bucket = bucket_labels[bucket_idx]

    pred = {
        "closure_prob": closure_prob,
        "closure_pred": int(closure_prob >= t1.get("recall_threshold", t1["threshold"])),
        "priority": "High" if high_prob >= 0.5 else "Low",
        "priority_prob": high_prob,
        "resolution_min": res_min,
        "aft_expected_min": aft_rank,
        "duration_bucket": duration_bucket,
        "severity": ex["severity_score"],
        "blocking_lanes": int(ex["blocking_lanes"]),
        "requires_tow": int(ex["requires_tow"]),
        "vehicles_involved": ex["vehicles_involved"],
        "incident_subtype": ex["incident_subtype"],
        "is_peak": int(X1["is_peak"].iloc[0]),
        "is_planned": int(record.get("is_planned", False)),
        "corridor": record.get("corridor", "Non-corridor"),
        "corridor_closure_rate": float(X1["corridor_closure_rate"].iloc[0]),
        "event_cause": record.get("event_cause", "incident"),
    }
    plan = recommend(pred)
    reasons = top_reasons(t1["model"], X1)
    return {"pred": pred, "plan": plan, "closure_reasons": reasons, "llm_extract": ex}


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    rec = dict(corridor="Tumkur Road", event_cause="tree_fall", veh_type=None,
               zone="West Zone 1", datetime=datetime(2024, 4, 1, 18, 0),
               is_planned=False, description="huge tree fallen blocking the road, crane needed")
    out = predict_all(rec)
    print("PRED:", {k: round(v, 3) if isinstance(v, float) else v for k, v in out["pred"].items()})
    print("\n" + out["plan"]["summary"])
    print("\nTop closure drivers:")
    for f, c in out["closure_reasons"]:
        print(f"  {f}: {c:+.3f}")
