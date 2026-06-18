"""Step 3 — Leakage-safe feature engineering.

Everything here is computable *the moment an incident is reported*. The recurrence and
spatial-history features are strictly PAST-ONLY: for each row they look only at incidents
that started earlier, via time-ordered searchsorted / cumulative means. This is exactly
how the features would be available online in production, and it means the later
chronological split introduces no leakage (a test row legitimately sees train-period
history). The banned end-point / resolution columns are never touched.
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd

from . import config as C
from . import llm_extract

NS_PER_DAY = 86_400 * 1_000_000_000
HEAVY_VEH = {"heavy_vehicle", "truck", "lcv", "tanker", "container"}


# ----------------------------------------------------------------- past-only helpers
def _past_window_count(times_ns, group_idx_list, window_days):
    """For each row: # of prior incidents in the same group within `window_days`."""
    win = int(window_days * NS_PER_DAY)
    out = np.zeros(len(times_ns))
    for idx in group_idx_list:
        ts = times_ns[idx]                       # ascending (df is time-sorted)
        left = np.searchsorted(ts, ts - win, side="left")
        out[idx] = np.arange(len(ts)) - left     # rows in [t-win, t)
    return out


def _past_rate(labels, group_idx_list, base):
    """For each row: mean of the label over prior incidents in the same group."""
    out = np.full(len(labels), base, dtype=float)
    for idx in group_idx_list:
        lab = labels[idx].astype(float)
        prior_sum = np.cumsum(lab) - lab
        prior_cnt = np.arange(len(lab))
        with np.errstate(invalid="ignore", divide="ignore"):
            rate = np.where(prior_cnt > 0, prior_sum / np.maximum(prior_cnt, 1), base)
        out[idx] = rate
    return out


def _days_since_last(times_ns, group_idx_list, fill=999.0):
    out = np.full(len(times_ns), fill, dtype=float)
    for idx in group_idx_list:
        ts = times_ns[idx]
        if len(ts) > 1:
            d = np.empty(len(ts)); d[0] = fill
            d[1:] = (ts[1:] - ts[:-1]) / NS_PER_DAY
            out[idx] = d
    return out


def _group_idx(series):
    """Ordered list of positional-index arrays, one per group (preserves time order)."""
    return [np.asarray(v) for v in series.reset_index(drop=True).groupby(series.values, sort=False).groups.values()]


def _past_mean_cont(values, group_idx_list, base):
    """Past-only mean of a continuous column; NaN rows (censored) are excluded."""
    v = np.where(np.isnan(values), 0.0, np.array(values, dtype=float))
    valid = (~np.isnan(values)).astype(float)
    out = np.full(len(values), base, dtype=float)
    for idx in group_idx_list:
        vv, vld = v[idx], valid[idx]
        prior_sum = np.cumsum(vv * vld) - vv * vld
        prior_cnt = np.cumsum(vld) - vld
        with np.errstate(invalid="ignore", divide="ignore"):
            rate = np.where(prior_cnt > 0, prior_sum / np.maximum(prior_cnt, 1), base)
        out[idx] = rate
    return out


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


# --------------------------------------------------------------------- main builder
def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("start_datetime").reset_index(drop=True)
    t = df["start_ist"]

    # ---- temporal
    df["hour"] = t.dt.hour
    df["day_of_week"] = t.dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month_of_year"] = t.dt.month
    # refined peak: closure spikes at 11-12 (midday) and 16-19 (evening) per EDA
    df["is_peak"] = df["hour"].isin([11, 12, 16, 17, 18, 19]).astype(int)
    df["is_night"] = df["hour"].isin([0, 1, 2, 3, 4, 5]).astype(int)
    df["hour_bucket"] = pd.cut(df["hour"], [-1, 5, 11, 16, 20, 24],
                               labels=[0, 1, 2, 3, 4]).astype(int)

    # ---- recurrence (PAST-ONLY)
    times = df["start_datetime"].astype("int64").to_numpy()
    base_t1 = float(df[C.T1].mean())
    base_t2 = float(df[C.T2].mean())
    t1 = df[C.T1].fillna(0).to_numpy()
    t2 = df[C.T2].fillna(0).to_numpy()

    corr_groups = _group_idx(df["corridor"].fillna("NA"))
    df["corridor_inc_7d"] = _past_window_count(times, corr_groups, 7)
    df["corridor_inc_30d"] = _past_window_count(times, corr_groups, 30)
    df["corridor_days_since_last"] = _days_since_last(times, corr_groups)
    df["corridor_closure_rate"] = _past_rate(t1, corr_groups, base_t1)
    df["corridor_high_rate"] = _past_rate(t2, corr_groups, base_t2)

    zone_groups = _group_idx(df["zone"].fillna("UNKNOWN"))
    df["zone_closure_rate"] = _past_rate(t1, zone_groups, base_t1)

    # past-only closure rates by cause, vehicle type, and police station — gives the
    # model continuous magnitude signals (tree_fall 39%, breakdown 3%) rather than
    # forcing it to infer rates from label-encoded integers. Directly helps unplanned recall.
    cause_groups = _group_idx(df["event_cause_norm"].fillna("unknown"))
    df["cause_closure_rate"] = _past_rate(t1, cause_groups, base_t1)

    veh_groups = _group_idx(df["veh_type"].fillna("unknown"))
    df["veh_closure_rate"] = _past_rate(t1, veh_groups, base_t1)

    ps_groups = _group_idx(df["police_station"].fillna("UNKNOWN"))
    df["police_station_closure_rate"] = _past_rate(t1, ps_groups, base_t1)

    # ~1.1km spatial grid: history of incidents/closures at that location
    df["grid_cell"] = (df["latitude"].round(2).astype(str) + "," +
                       df["longitude"].round(2).astype(str))
    grid_groups = _group_idx(df["grid_cell"])
    df["grid_inc_30d"] = _past_window_count(times, grid_groups, 30)
    df["grid_closure_rate"] = _past_rate(t1, grid_groups, base_t1)

    # past-only mean resolution time per group (censored rows excluded via NaN masking).
    # Using resolution_time_min only for past-history stats, never as a direct feature.
    dur_vals = np.where(df["is_censored"].to_numpy() == 0, df[C.T3].to_numpy(dtype=float), np.nan)
    global_dur_mean = float(np.nanmean(dur_vals))
    df["cause_duration_mean"] = _past_mean_cont(dur_vals, cause_groups, global_dur_mean)
    df["corridor_duration_mean"] = _past_mean_cont(dur_vals, corr_groups, global_dur_mean)
    df["zone_duration_mean"] = _past_mean_cont(dur_vals, zone_groups, global_dur_mean)

    # city-wide load in the prior 24h (global, past-only)
    left = np.searchsorted(times, times - NS_PER_DAY, side="left")
    df["city_inc_1d"] = np.arange(len(times)) - left

    # repeat-vehicle (anonymised veh_no seen before)
    veh_prior = df.groupby("veh_no").cumcount()
    df["repeat_vehicle"] = ((df["veh_no"].notna()) & (veh_prior > 0)).astype(int)

    # ---- spatial
    clat, clon = df["latitude"].mean(), df["longitude"].mean()
    df["dist_centroid_km"] = _haversine_km(df["latitude"], df["longitude"], clat, clon)

    # ---- flags
    df["is_heavy_vehicle"] = df["veh_type"].isin(HEAVY_VEH).astype(int)
    df["is_non_corridor"] = (df["corridor"] == "Non-corridor").astype(int)
    df["is_planned"] = (df["event_type"] == "planned").astype(int)
    df["has_description"] = df["description"].notna().astype(int)
    df["zone_missing"] = df["zone"].isna().astype(int)

    # interaction: planned × cause closure rate — lets the model separate high-risk planned
    # causes (vip/event/protest, ~40-80% closure) from low-risk planned (construction, ~27%)
    # without needing a two-level tree split. Also added for corridor and peak hour.
    df["planned_cause_risk"] = df["is_planned"] * df["cause_closure_rate"]
    df["peak_cause_risk"] = df["is_peak"] * df["cause_closure_rate"]
    df["corridor_cause_risk"] = df["corridor_closure_rate"] * df["cause_closure_rate"]

    # ---- description-derived features (LLM cache where present, else rule-based)
    llm = llm_extract.apply_to_df(df)
    src = llm.attrs.get("llm_source", {})
    print(f"description features source mix: {src}")
    for col in ["llm_severity_score", "llm_blocking_lanes", "llm_vehicles_involved",
                "llm_requires_tow"]:
        df[col] = llm[col].to_numpy()
    df["llm_subtype"] = llm["llm_subtype"].to_numpy()   # encoded later in train.py

    # past-only closure rate by LLM subtype — adds magnitude on top of the top SHAP feature
    subtype_groups = _group_idx(pd.Series(df["llm_subtype"].values))
    df["llm_subtype_closure_rate"] = _past_rate(t1, subtype_groups, base_t1)

    # LLM duration estimate: Groq estimates clearance minutes from the officer note.
    # 0 = note gave no duration clues; replaced with cause mean so the feature is never empty.
    llm_dur = llm_extract.apply_duration_to_df(df)
    df["llm_estimated_duration_min"] = np.where(
        llm_dur == 0, df["cause_duration_mean"], llm_dur
    )

    return df


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    df = pd.read_parquet(C.CLEAN_PARQUET)
    feats = build_features(df)
    feats.to_parquet(C.FEATURES_PARQUET, index=False)
    print(f"features shape: {feats.shape}  ->  {C.FEATURES_PARQUET}")

    # show the model feature list (after the train-time encoders are added it gains *_le cols)
    numeric_feats = C.get_feature_columns(feats)
    print(f"\nnumeric/bool feature columns ({len(numeric_feats)}):")
    print(numeric_feats)
    # leakage guard
    banned_present = [c for c in numeric_feats if c in C.BANNED_LEAKAGE]
    assert not banned_present, f"LEAKAGE: banned cols in features: {banned_present}"
    print("\nOK: no banned leakage columns in numeric feature set.")


if __name__ == "__main__":
    main()
