"""Step 1 — Load, clean, derive targets, save a tidy chronological parquet.

Key decisions (grounded in the EDA, see plan):
  * event_cause casing dupes normalized (Debris/debris, 'Fog / Low Visibility').
  * Missing start_datetime (116 rows, mostly planned events) imputed from created_date
    (median lag start->created is ~1.5 min, so created_date ~= report time).
  * T3 = modified_datetime - start_datetime in minutes. For the AFT survival model we
    also keep `is_censored` (status == 'active' -> incident not yet resolved -> the true
    duration is >= elapsed time). Uncensored rows require value > 0.
  * All-null bookkeeping columns dropped.
  * Rows sorted by start_datetime — the chronological backbone for splitting + recurrence.
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd

from . import config as C

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATETIME_COLS = [
    "start_datetime", "end_datetime", "modified_datetime", "created_date",
    "closed_datetime", "resolved_datetime",
]

# Casing / spelling normalization for event_cause.
CAUSE_FIXES = {
    "debris": "debris",
    "fog / low visibility": "fog_low_visibility",
}


def _norm_cause(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    return CAUSE_FIXES.get(s, s)


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(C.RAW_CSV, low_memory=False)
    for c in DATETIME_COLS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- event_cause normalization
    df["event_cause_norm"] = df["event_cause"].map(_norm_cause)

    # --- impute start_datetime from created_date where missing (mostly planned events)
    df["start_imputed"] = df["start_datetime"].isna().astype(int)
    df["start_datetime"] = df["start_datetime"].fillna(df["created_date"])
    df = df[df["start_datetime"].notna()].copy()  # drop the few with neither
    df["start_ist"] = df["start_datetime"].dt.tz_convert("Asia/Kolkata")

    # --- T1: requires_road_closure -> 1/0
    df[C.T1] = df["requires_road_closure"].map(
        {True: 1, False: 0, "True": 1, "False": 0, "TRUE": 1, "FALSE": 0}
    ).astype("Int64")

    # --- T2: priority High -> 1, Low -> 0 (drop the 2 NaN priorities)
    df[C.T2] = df["priority"].map({"High": 1, "Low": 0}).astype("Int64")

    # --- T3: resolution time (minutes) + censoring info for the AFT model
    delta = (df["modified_datetime"] - df["start_datetime"]).dt.total_seconds() / 60.0
    df["resolution_time_raw_min"] = delta
    df["is_censored"] = (df["status"] == "active").astype(int)
    # Uncensored = closed/resolved with a positive elapsed time.
    uncensored_ok = df["status"].isin(["closed", "resolved"]) & (delta > 0)
    # For active (censored) rows, elapsed time is a lower bound on true duration.
    df[C.T3] = np.where(uncensored_ok | ((df["is_censored"] == 1) & (delta > 0)), delta, np.nan)

    # --- drop fully-null / unusable bookkeeping columns
    null_rate = df.isna().mean()
    drop_null = [c for c in df.columns if null_rate.get(c, 0) >= 0.999
                 and c not in (C.T3, "resolution_time_raw_min")]
    df = df.drop(columns=drop_null, errors="ignore")

    # --- chronological order (backbone for split + past-only recurrence features)
    df = df.sort_values("start_datetime").reset_index(drop=True)
    return df


def main():
    raw = load_raw()
    print(f"raw shape: {raw.shape}")
    df = clean(raw)

    df.to_parquet(C.CLEAN_PARQUET, index=False)
    print(f"clean shape: {df.shape}  ->  {C.CLEAN_PARQUET}")

    # --- sanity report
    n = len(df)
    t1 = df[C.T1].mean()
    t2 = df[C.T2].mean()
    res_uncens = df.loc[df["is_censored"] == 0, C.T3]
    print("\n=== target sanity ===")
    print(f"T1 requires_road_closure: {t1*100:.1f}% positive (expect ~8.3%)")
    print(f"T2 priority High        : {t2*100:.1f}% (expect ~62%), NaN={df[C.T2].isna().sum()}")
    print(f"T3 rows with value      : {df[C.T3].notna().sum()} "
          f"(censored/active={int((df['is_censored']==1).sum())}, "
          f"uncensored={int(res_uncens.notna().sum())})")
    print(f"T3 uncensored median min: {res_uncens.median():.1f}")
    print(f"start imputed rows      : {int(df['start_imputed'].sum())}")
    print(f"date range              : {df['start_datetime'].min()} -> {df['start_datetime'].max()}")
    print(f"event_type counts       : {df['event_type'].value_counts().to_dict()}")
    assert 0.05 < t1 < 0.12, "T1 positive rate off — check mapping"
    assert df[C.T1].isna().sum() == 0, "T1 has NaNs"
    print("\nOK: data_prep complete.")


if __name__ == "__main__":
    main()
