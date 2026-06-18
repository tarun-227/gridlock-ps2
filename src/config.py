"""Central configuration: paths, leakage controls, feature policy, model params.

This is the single source of truth for *what the models are allowed to see*. The
BANNED_LEAKAGE list is the most important object in the repo: end-point coordinates
are recorded only *because* a closure happened, so they are a ~98% proxy for the T1
label and are NOT known at report time. Excluding them everywhere is what separates
an honest model from a hollow 0.98-F1 demo.
"""
from __future__ import annotations
from pathlib import Path

# --------------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

RAW_CSV = DATA_RAW / "incidents.csv"
CLEAN_PARQUET = DATA_PROC / "incidents_clean.parquet"
FEATURES_PARQUET = DATA_PROC / "incidents_features.parquet"
LLM_CACHE = DATA_PROC / "llm_features_cache.json"
LLM_DURATION_CACHE = DATA_PROC / "llm_duration_cache.json"
DURATION_BUCKET_BINS = [0, 60, 180, 480, float("inf")]
DURATION_BUCKET_LABELS = ["<1h", "1-3h", "3-8h", ">8h"]
METRICS_JSON = MODELS_DIR / "metrics.json"

for _d in (DATA_RAW, DATA_PROC, MODELS_DIR, REPORTS_DIR, FIGURES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------- general
SEED = 42
# Chronological split fractions (NOT random — data is time-ordered).
TRAIN_FRAC, VAL_FRAC = 0.70, 0.15  # test = remainder

# --------------------------------------------------------------------------- targets
T1 = "requires_road_closure"      # binary
T2 = "priority_high"              # binary (1 = High)
T3 = "resolution_time_min"        # regression (minutes), survival target
TARGETS = [T1, T2, T3]

# ------------------------------------------------------------- LEAKAGE / EXCLUSIONS
# Recorded only after/because the incident is resolved or a closure happened.
BANNED_LEAKAGE = [
    "endlatitude", "endlongitude", "end_address", "has_end_point", "incident_length_km",
    "end_datetime", "modified_datetime", "closed_datetime", "resolved_datetime",
    "resolved_at_address", "resolved_at_latitude", "resolved_at_longitude",
    "closed_by_id", "resolved_by_id", "status",
    "resolution_time_min", "resolution_time_raw_min", "is_censored",
]

# Identifiers / free-text / raw datetimes / bookkeeping that are never model features.
ALWAYS_EXCLUDE = [
    "id", "address", "description", "veh_no", "kgid", "gba_identifier",
    "start_datetime", "created_date", "modified_datetime", "start_ist",
    "client_id", "created_by_id", "last_modified_by_id", "assigned_to_police_id",
    "citizen_accident_id", "comment", "meta_data", "map_file", "route_path",
    "junction", "grid_cell",  # high-cardinality raw strings (their derived stats are kept)
    "event_cause_norm",       # keep only the label-encoded version
    "age_of_truck", "cargo_material", "reason_breakdown",  # ~96%+ null, no signal
    "veh_type", "corridor", "zone", "police_station", "llm_subtype",  # raw cats (use *_le)
    "event_type", "priority", "requires_road_closure",    # raw target sources
    "authenticated", "direction",
]

# Features that encode corridor identity — dropped for the corridor-blind T2 variant
# that tests whether incident characteristics alone can recover the priority rule.
CORRIDOR_FEATURES = [
    "corridor_le", "is_non_corridor", "corridor_inc_7d", "corridor_inc_30d",
    "corridor_closure_rate", "corridor_high_rate", "corridor_days_since_last",
    "corridor_duration_mean", "corridor_cause_risk",  # derived from corridor stats
]

# ------------------------------------------------------------------------- LLM step
# Two interchangeable backends for description mining. Groq (cloud, fast, free tier) is
# preferred when a key is available; Ollama qwen2.5:3b is the local fallback. Both only
# process the dataset's own `description` text (PS2-compliant). The key is read from the
# GROQ_API_KEY env var or a gitignored .secrets/groq.key file — never hardcoded in source.
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"   # 14,400 req/day free tier; fast (~0.6s/call)
_SECRETS = ROOT / ".secrets" / "groq.key"


def groq_api_key():
    import os
    k = os.environ.get("GROQ_API_KEY")
    if k:
        return k.strip()
    if _SECRETS.exists():
        return _SECRETS.read_text(encoding="utf-8").strip()
    return None
LLM_FEATURES = [
    "llm_severity_score", "llm_blocking_lanes", "llm_vehicles_involved",
    "llm_requires_tow", "llm_subtype_le",
]
LLM_SUBTYPES = [
    "vehicle_breakdown", "collision", "tree_or_debris", "waterlogging_or_pothole",
    "construction_or_utility", "crowd_or_event", "vip_or_procession",
    "congestion_only", "other",
]

# String categoricals label-encoded in train.py (fit on TRAIN only, unseen -> -1).
# Encoded column name convention is f"{col}_le".
CATEGORICAL_COLS = [
    "corridor", "event_cause_norm", "veh_type", "zone", "police_station", "llm_subtype",
]

# ----------------------------------------------------------------- model params
XGB_CLF_PARAMS = dict(
    n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8,
    colsample_bytree=0.8, min_child_weight=3, reg_lambda=1.0, gamma=0.1,
    eval_metric="aucpr", tree_method="hist", random_state=SEED, n_jobs=-1,
)
XGB_REG_PARAMS = dict(
    n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.8,
    colsample_bytree=0.8, min_child_weight=5, reg_lambda=2.0,
    objective="reg:squarederror", tree_method="hist", random_state=SEED, n_jobs=-1,
)
# XGBoost AFT survival params for T3 (handles right-censored 'active' incidents).
# dict literal because 'lambda' is a reserved Python keyword and must be a string key.
XGB_AFT_PARAMS = {
    "objective": "survival:aft", "eval_metric": "aft-nloglik",
    "aft_loss_distribution": "normal", "aft_loss_distribution_scale": 1.20,
    "max_depth": 5, "eta": 0.05, "subsample": 0.8, "colsample_bytree": 0.8,
    "min_child_weight": 3, "lambda": 1.0, "tree_method": "hist", "seed": SEED,
}
AFT_NUM_BOOST_ROUND = 600
# The log1p operational regressor caps the target at 6h: durations beyond that are the
# civic-process tail (potholes/construction) that report-time features cannot predict.
# This keeps point estimates in the actionable range. The artifact-dominated target means
# the median is near-optimal — we report this honestly rather than overfitting the tail.
T3_REG_CAP_MIN = 360


def get_feature_columns(df, corridor_blind: bool = False):
    """All engineered model features: everything except targets, ids, leakage.

    Selects numeric/bool columns only (categoricals must already be label-encoded).
    """
    import pandas as pd
    exclude = set(TARGETS) | set(BANNED_LEAKAGE) | set(ALWAYS_EXCLUDE)
    if corridor_blind:
        exclude |= set(CORRIDOR_FEATURES)
    cols = []
    for c in df.columns:
        if c in exclude:
            continue
        if pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]):
            cols.append(c)
    return cols
