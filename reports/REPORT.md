# Event-Driven Congestion: Forecasting Impact & Recommending Resources
### PS2 — Flipkart × Bengaluru Traffic Police · Prototype submission

## 1. Problem & approach
Planned and unplanned events (rallies, festivals, VIP movement, construction, breakdowns,
tree-fall, water-logging) cause localised traffic breakdowns across Bengaluru. Today, impact
is not quantified in advance and resource deployment is experience-driven. We build a
**decision-support system** that, the moment an incident is reported, predicts its impact and
recommends a concrete deployment plan — using **only the provided dataset** (8,171 incidents,
Nov 2023–Apr 2024).

Three predictions, then a recommendation layer:

| Target | Type | Operational question |
|---|---|---|
| **T1** `requires_road_closure` | binary | Will this need a road closure? |
| **T2** `priority` (High/Low) | binary | What dispatch priority? |
| **T3** `resolution_time` | regression / survival | How long until cleared? |

→ **Recommendation engine**: manpower, barricading, diversion (Section 6).

## 2. The three data findings that shaped everything
A naive pipeline scores ~0.98 F1 on closure and ~1.0 on priority — and would be **wrong**.
Our EDA (`notebooks/01_eda.ipynb`) shows why, and we model accordingly.

**(a) End-point coordinates leak the closure label.** Of 689 incidents with a non-zero
`endlatitude`, **676 (98%) required closure**; of 7,484 without an end point, **0** did. The end
point is recorded *because* a closure happened — it is **not known at report time**. We **ban**
`endlat/endlon`, `has_end_point`, `incident_length_km`, `end_address` and all resolution-time
fields from every model. This is the single most important modelling decision.

**(b) Priority is a deterministic rule.** `priority = (corridor ≠ "Non-corridor")` with **zero**
exceptions across all 22 corridors. T2 is a classification *rule*, not a prediction problem. We
report it honestly and additionally train a **corridor-blind** model to test recoverability.

**(c) Resolution time is partly a recording artifact.** For the dominant `vehicle_breakdown`
class (60% of rows), 61% of `modified − start` values cluster in 120–180 min — records are
auto-modified ~2h after start regardless of real clearance. Resolution is **flat across priority
(134 vs 135 min) and closure (132 vs 135)** but spans **500×** across cause (congestion ~2.5h →
potholes ~8 days). T3 therefore mixes an artifact with a civic-process clock and is only weakly
predictable — itself an actionable finding for BTP (Section 7).

See `reports/figures/eda/` (figures 01–08), especially `07_leakage_determinism_audit.png`.

## 3. Methodology (research-grounded)
- **Chronological 70/15/15 split** by `start_datetime` (never random — the data is time-ordered).
  Recurrence features are strictly **past-only** (time-ordered `searchsorted`/cumulative means),
  so a test row only ever sees earlier history — exactly as in production.
- **Features (leakage-safe, 43):** temporal (refined peak 11–12 & 16–19h), past-only recurrence
  (corridor/zone/grid/cause/veh-type/police-station/llm-subtype closure rates, incident counts,
  days-since-last, city load), interaction features (`planned_cause_risk`, `peak_cause_risk`,
  `corridor_cause_risk`), internal spatial (lat/lon, distance-to-centroid), flags
  (`is_planned`, `is_heavy_vehicle`, `is_non_corridor`…), and **description-derived features**
  (severity 1–5, lane-blocking, vehicles-involved, tow-needed, subtype) extracted from the note.
- **Description mining (hybrid):** **Groq `llama-3.1-8b-instant`** (batched, 4 concurrent workers,
  ~2 notes/s) extracted structured features from all 5,475 unique descriptions — 99% LLM-sourced,
  1% rule-based fallback. A fast deterministic multilingual rule-based extractor provides instant
  fallback and live-inference coverage. Both paths process only text already in the dataset
  (PS-compliant). For the dashboard live path, Groq is called on new descriptions not yet in cache.
- **Models (XGBoost):**
  - *T1*: classifier + `scale_pos_weight`, then **isotonic-calibrated probabilities** (the
    recommendation engine consumes probability) and a PR-curve threshold.
  - *T2*: classifier (full) + corridor-blind variant.
  - *T3*: **`survival:aft`** — the literature-standard for heavy-tailed, **right-censored**
    durations; it *uses* the 1,007 ongoing "active" incidents as `[elapsed, +∞)` (a naive
    regressor discards them) — plus a 6h-capped log1p regressor for actionable point estimates.

Literature basis: XGBoost AFT (arXiv:2006.04920); Tang et al. 2020 (XGBoost incident clearance
time); text-mining + ensembles for incident duration (Sci. Reports 2022); imbalanced
crash-severity handling (MDPI 2020); planned-special-event congestion prediction.

## 4. Results (held-out chronological test set, n=1,226)

**T1 — road closure (the genuinely predictive target)**

| Metric | Model | Baseline |
|---|---|---|
| PR-AUC (primary) | **0.384** | 0.086 (majority) → **4.48× lift** |
| ROC-AUC | **0.836** | 0.5 |
| Weighted F1 | 0.886 | 0.873 |
| Recall @ ops threshold 0.10 | **0.667** (precision 0.300) | — |

Realistic (not suspiciously perfect) → confirms no leakage. Probabilities are calibrated
(`reports/figures/t1_calibration.png`). Top SHAP drivers: **`llm_subtype_le`** (description
incident type), **`is_planned`**, city load, vehicle type, corridor recurrence — i.e. the
event-driven + text + recurrence story exactly as hypothesised.

**Planned vs unplanned breakdown (operationally important):**

| Incident type | n (test) | Recall | F1 |
|---|---|---|---|
| Planned | 27 | **1.000** | 0.736 |
| Unplanned | 1,199 | **0.532** | 0.889 |

Planned recall is perfect — every planned closure caught. Unplanned recall improved from 0.362
to 0.532 through two feature engineering steps:

1. **Past-only rate features** (`cause_closure_rate`, `veh_closure_rate`,
   `police_station_closure_rate`, `llm_subtype_closure_rate`) — give the model explicit
   continuous closure-probability signals per category rather than label-encoded integers.
2. **Interaction features** (`planned_cause_risk = is_planned × cause_closure_rate`,
   `peak_cause_risk`, `corridor_cause_risk`) — let the model separate high-risk planned
   causes (public_event/VIP at 46–80% closure) from low-risk planned (construction, 27%)
   without needing a two-level tree split. This also restored planned recall to 1.0.

**T2 — priority (honest framing)**

| Model | Weighted F1 |
|---|---|
| Full XGBoost | 0.9992 |
| Corridor rule baseline | 0.9984 |
| **Corridor-blind** XGBoost | **0.923** |

The full model barely beats the rule (priority *is* the corridor rule). Notably, the
corridor-blind model still recovers priority at F1≈0.923 from incident characteristics alone
— meaning event cause, vehicle type, time-of-day, and description severity together contain
enough signal to assign correct dispatch priority even for incidents on unlabelled or new roads.
BTP could extend priority assignment to locations not yet designated as formal corridors.

**T3 — resolution time (re-framed as duration bucket prediction)**

Point-minute regression against this target is near-useless because 60% of records are
auto-modified at ~130 min regardless of actual clearance. We re-frame T3 as an **operational
bucket classifier** (4 classes: <1h / 1-3h / 3-8h / >8h) — the question dispatchers actually need.

| Metric | Model | Baseline |
|---|---|---|
| Bucket accuracy | **65.8%** | 57.9% (always "1-3h") |
| 1-3h F1 (dominant bucket) | **0.800** | — |
| >8h F1 (civic processes) | **0.645** | — |
| AFT C-index (ranking) | **0.598** | 0.5 (random) |

The `llm_estimated_duration_min` feature — Groq's clearance estimate from the officer's own note
("crane needed, truck overturned" → ~240 min; "minor breakdown moved aside" → ~45 min) — is the
top driver for the bucket classifier. Three past-only duration mean features (`cause_duration_mean`,
`corridor_duration_mean`, `zone_duration_mean`) provide group-level priors.

Per-cause breakdown still reveals where the model is and isn't useful:

| Cause | MAE (min) | Actionable? |
|---|---|---|
| accident | 35 | Yes — short, predictable |
| congestion | 37 | Yes |
| procession | 80 | Yes |
| vehicle_breakdown | 115 | Yes — the dominant class |
| construction | 3,220 | No — weeks-long civic process |
| public_event | 3,951 | No — event-schedule dependent |
| tree_fall / others | 2,400 | No |
| pot_holes / road_conditions | 8,000–9,600 | No — unpredictable civic tail |

The model is practically useful for the short-clearance causes (accidents, congestion,
breakdowns) and should not be used for duration estimates on multi-day civic works.

## 5. Explainability
Per-model global SHAP (`reports/figures/t1_shap.png`, `t3_shap.png`) and **per-incident** SHAP
in the dashboard (top drivers for each forecast).

**T1 top SHAP contributors (mean |SHAP| on test set):**

| Feature | Mean |SHAP| | What it means |
|---|---|---|
| `llm_subtype_le` | 0.229 | Incident type from officer note (VIP/crowd → high risk) |
| `is_planned` | 0.220 | Planned events 36% closure rate vs 6.6% unplanned |
| `city_inc_1d` | 0.214 | City-wide load at report time |
| `veh_type_le` | 0.207 | Heavy vehicles / tankers correlate with closures |
| `grid_closure_rate` | 0.155 | Historical closure rate of the ~1km grid cell |
| `corridor_days_since_last` | 0.169 | Recency of last corridor incident |
| `corridor_closure_rate` | 0.146 | Long-run corridor closure history |

The officer's own description (`llm_subtype_le`) is the top predictor — directly interpretable:
a note classified as `vip_or_procession` or `crowd_or_event` raises closure probability most.
This validates the LLM text extraction step and gives BTP a concrete signal from existing workflow.

## 6. From prediction to deployment (recommendation engine)
`src/recommend.py` maps the three predictions into an explainable plan:
- **Manpower** = base(priority) + closure-risk + severity + peak + chronic-corridor + planned-event.
- **Barricading** triggered when closure probability ≥ 0.4 or severity ≥ 4; count scales with risk.
- **Diversion** to the nearest alternate corridor (internally-derived corridor families) when a
  named corridor is likely to close.
- **Alert level** LOW→CRITICAL; tow/crane flagged from the note.

Example (tree-fall, Tumkur Road, evening peak): *CRITICAL · 13 officers · 12 barricades · divert
to West of Chord Road · dispatch crane · ~2.6h clearance* — every number with a stated rationale.

## 7. Post-event learning & recommendations to BTP
- **Learning loop:** each closed incident feeds the past-only corridor/zone/grid recurrence
  features; re-running `features → train` lets the system improve continuously.
- **Data-quality finding:** capturing a true **"road cleared" timestamp** (distinct from the
  record-modification time) would unlock genuine resolution-time forecasting — currently the
  single biggest limiter.

## 8. Limitations
Single ~5-month window (no full seasonality); no attendance/weather (external data disallowed);
T3 ceiling set by the recording artifact; closure recall is moderate (precision/recall is a
deliberate operating-point choice — missing a closure is costly).

## 9. Reproduce
```
pip install -r requirements.txt
python -m src.data_prep        # clean parquet
python -m src.features         # leakage-safe features (LLM cache + rule fallback)
python -m src.train            # 3 models + variants
python -m src.evaluate         # metrics.json + SHAP + calibration figures
python -m src.eda              # EDA figures   (notebooks/01_eda.ipynb for the full EDA)
streamlit run app/dashboard.py # live demo
```
Optional (adds Groq API key to `.secrets/groq.key`): `python -m src.llm_extract` fills or extends
the description-feature cache (~2 notes/s via Groq, resume-safe, rule-based fallback always active).
