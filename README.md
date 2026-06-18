# PS2 — Event-Driven Congestion (Flipkart × Bengaluru Traffic Police)

Forecast the traffic impact of an incident the moment it is reported, and recommend
manpower / barricading / diversion. Built on the **provided dataset only**.

Predicts three targets and turns them into an operations plan:
- **T1** `requires_road_closure` (binary) · **T2** `priority` (High/Low) · **T3** `resolution_time` (minutes)
- → **recommendation engine** (officers, barricades, diversion, alert level)

See **`reports/REPORT.md`** for the full write-up and results, and
**`notebooks/01_eda.ipynb`** for the exploratory analysis.

## Headline: why this isn't a naive pipeline
The data hides three traps; handling them honestly is the core contribution:
1. **End-point coordinates leak the closure label** (98% proxy) → banned from all models.
2. **Priority is a deterministic corridor rule** → modelled + framed honestly.
3. **Resolution time is partly a recording artifact** → AFT survival + honest, robust metrics.

## Setup
```bash
pip install -r requirements.txt          # pandas, scikit-learn, xgboost, streamlit, lifelines, ...
# Local LLM (optional, for description mining): install Ollama, then `ollama pull qwen2.5:3b`
```
Windows note: scripts set UTF-8 internally; if you call Python directly, use
`PYTHONIOENCODING=utf-8` (notes contain Kannada).

## Run order
```bash
python -m src.data_prep        # 1. clean + derive targets -> data/processed/incidents_clean.parquet
python -m src.features         # 2. leakage-safe features  -> incidents_features.parquet
python -m src.train            # 3. train T1/T2/T3 (+ variants) -> models/
python -m src.evaluate         # 4. test metrics + SHAP + calibration -> models/metrics.json, reports/figures/
python -m src.eda              # 5. EDA figures -> reports/figures/eda/
streamlit run app/dashboard.py # 6. live demo (Predict + Insights tabs)
```
Optional description mining (slow on CPU/2GB GPU, ~15–20h for full coverage, resume-safe;
the rule-based fallback gives full coverage instantly so this is enrichment only):
```bash
python -m src.llm_extract --limit 50   # smoke test
python -m src.llm_extract              # full, cached to data/processed/llm_features_cache.json
```

## Layout
```
src/
  config.py        paths, per-target feature lists, BANNED leakage list, model params
  data_prep.py     load, clean, normalize, impute start, derive targets
  features.py      temporal / past-only recurrence / spatial / encodings / description features
  text_features.py fast multilingual rule-based description extractor (backbone)
  llm_extract.py   Ollama qwen2.5:3b extractor, cached + resume-safe
  prepare.py       chronological split + train-only encoding (shared by train/evaluate)
  train.py         T1 (calibrated) · T2 (+corridor-blind) · T3 (AFT survival + log1p regressor)
  evaluate.py      PR-AUC/F1/calibration · C-index/MAE · baselines · SHAP · breakdowns
  recommend.py     predictions -> manpower / barricading / diversion (explainable rules)
  predict.py       single-incident inference glue (used by the dashboard)
  eda.py           EDA figure generators
app/dashboard.py   Streamlit decision-support UI
notebooks/01_eda.ipynb   executed EDA
reports/REPORT.md        full report  ·  models/metrics.json  test metrics
```

## Key results (held-out chronological test set)
- **T1 closure** PR-AUC **0.30** (3.5× majority baseline), ROC-AUC 0.78, calibrated probabilities.
- **T2 priority** F1 **0.999** (≈ corridor rule); corridor-blind model still recovers it at 0.92.
- **T3 duration** AFT C-index **0.59** (uses 1,007 censored incidents); edges constant baseline on
  R²/RMSE — median is near-optimal (artifact-limited; a data-quality recommendation for BTP).

PS2 compliance: only the provided dataset is used; all features (including LLM-extracted ones) are
engineered from existing columns.
