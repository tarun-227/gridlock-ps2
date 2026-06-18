"""Shared data preparation: chronological split + train-only categorical encoding.

Kept separate so train.py and evaluate.py build the *exact same* splits/encoders
(single source of truth, no leakage from re-fitting on different data).
"""
from __future__ import annotations
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config as C


@dataclass
class Prepared:
    df: pd.DataFrame                       # full frame + encoded *_le cols + 'split'
    encoders: dict                         # {col: {category: code}}
    context: dict = field(default_factory=dict)

    def mask(self, split):
        return self.df["split"] == split


def _fit_encoder(train_vals: pd.Series) -> dict:
    cats = [c for c in pd.unique(train_vals.dropna())]
    return {c: i for i, c in enumerate(sorted(map(str, cats)))}


def _apply_encoder(vals: pd.Series, mapping: dict) -> np.ndarray:
    return vals.astype("object").map(lambda x: mapping.get(str(x), -1)).astype(int).to_numpy()


def prepare() -> Prepared:
    df = pd.read_parquet(C.FEATURES_PARQUET)
    df = df.sort_values("start_datetime").reset_index(drop=True)

    # ---- chronological split (NOT random)
    n = len(df)
    i_tr, i_va = int(n * C.TRAIN_FRAC), int(n * (C.TRAIN_FRAC + C.VAL_FRAC))
    split = np.array(["train"] * n, dtype=object)
    split[i_tr:i_va] = "val"
    split[i_va:] = "test"
    df["split"] = split
    train_mask = df["split"] == "train"

    # ---- categorical encoding (fit on TRAIN only, unseen -> -1)
    encoders = {}
    for col in C.CATEGORICAL_COLS:
        if col not in df.columns:
            continue
        mapping = _fit_encoder(df.loc[train_mask, col])
        encoders[col] = mapping
        df[f"{col}_le"] = _apply_encoder(df[col], mapping)

    # ---- context for the dashboard / single-incident featurization (train-derived)
    tr = df[train_mask]
    feat_cols = C.get_feature_columns(df)
    context = {
        "centroid": (float(df["latitude"].mean()), float(df["longitude"].mean())),
        "base_closure_rate": float(tr[C.T1].mean()),
        "base_high_rate": float(tr[C.T2].mean()),
        "global_median_res_min": float(tr.loc[tr["is_censored"] == 0, C.T3].median()),
        "city_inc_1d_median": float(tr["city_inc_1d"].median()),
        # median feature vector — the robust default template for a new incident
        "feature_medians": tr[feat_cols].astype(float).median().round(4).to_dict(),
        "encoders": encoders,
        # per-corridor latest recurrence stats (last known row per corridor in train+val)
        "corridor_stats": (
            df[df["split"].isin(["train", "val"])]
            .groupby("corridor")
            .agg(corridor_closure_rate=("corridor_closure_rate", "last"),
                 corridor_high_rate=("corridor_high_rate", "last"),
                 corridor_inc_7d=("corridor_inc_7d", "mean"),
                 corridor_inc_30d=("corridor_inc_30d", "mean"),
                 corridor_days_since_last=("corridor_days_since_last", "mean"))
            .round(4).to_dict("index")
        ),
        "zone_closure_rate": (
            df[df["split"].isin(["train", "val"])]
            .groupby("zone")["zone_closure_rate"].last().round(4).to_dict()
        ),
        "cause_duration_mean": (
            df[df["split"].isin(["train", "val"])]
            .groupby("event_cause_norm")["cause_duration_mean"].last().round(1).to_dict()
        ),
        "cause_closure_rate": (
            df[df["split"].isin(["train", "val"])]
            .groupby("event_cause_norm")["cause_closure_rate"].last().round(4).to_dict()
        ),
        "veh_closure_rate": (
            df[df["split"].isin(["train", "val"])]
            .groupby("veh_type")["veh_closure_rate"].last().round(4).to_dict()
        ),
        "police_station_closure_rate": (
            df[df["split"].isin(["train", "val"])]
            .groupby("police_station")["police_station_closure_rate"].last().round(4).to_dict()
        ),
        "llm_subtype_closure_rate": (
            df[df["split"].isin(["train", "val"])]
            .groupby("llm_subtype")["llm_subtype_closure_rate"].last().round(4).to_dict()
        ),
        "corridors": sorted(df["corridor"].dropna().unique().tolist()),
        "event_causes": sorted(df["event_cause_norm"].dropna().unique().tolist()),
        "veh_types": sorted(df["veh_type"].dropna().unique().tolist()),
        "zones": sorted(df["zone"].dropna().unique().tolist()),
    }
    return Prepared(df=df, encoders=encoders, context=context)


def split_xy(prep: Prepared, target: str, corridor_blind: bool = False,
             require_target: bool = True):
    """Return (Xtr,ytr,Xva,yva,Xte,yte, feat_cols) for a classification/regression target."""
    df = prep.df
    feat_cols = C.get_feature_columns(df, corridor_blind=corridor_blind)
    out = {}
    for sp in ("train", "val", "test"):
        sub = df[df["split"] == sp]
        if require_target:
            sub = sub[sub[target].notna()]
        out[sp] = (sub[feat_cols].astype(float), sub[target])
    return (*out["train"], *out["val"], *out["test"], feat_cols)
