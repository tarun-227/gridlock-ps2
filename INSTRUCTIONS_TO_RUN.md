# Instructions to Run — GridLock: Event-Driven Congestion Forecasting

> Tested on Python 3.12, Windows 11. Steps also work on Linux/Mac with equivalent commands.

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.9+ | all pipeline steps |
| Node.js | 18+ | pitch deck build script (optional) |
| Groq API key | — | optional; LLM cache already included |

---

## Quick start (pre-built artifacts — fastest for reviewers)

All model artifacts, LLM caches, and metrics are already committed to the repo.
You can run the dashboard immediately without retraining.

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd grid_lock_phase_2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the dashboard
streamlit run app/dashboard.py
```

Open the browser at the URL shown (default: http://localhost:8501).

- **Predict & Recommend tab**: enter corridor / cause / description → get closure probability, priority, duration bucket, and deployment plan.
- **Insights tab**: model metrics vs baselines, SHAP charts, data findings.

---

## Full pipeline (re-run everything from scratch)

Run steps in order. Each step is independent and checkpointed.

```bash
# 0. Install dependencies
pip install -r requirements.txt

# 1. Clean the raw data → incidents_clean.parquet
python -m src.data_prep

# 2. Build leakage-safe features (uses LLM cache; rule-based fallback if no API key)
python -m src.features

# 3. Train all three models (T1 closure, T2 priority, T3 duration)
python -m src.train

# 4. Evaluate → metrics.json + SHAP figures + calibration curve
python -m src.evaluate

# 5. Launch the dashboard
streamlit run app/dashboard.py
```

Expected runtimes on a laptop (i7 / 16 GB RAM):

| Step | Time |
|---|---|
| data_prep | ~10 s |
| features | ~30 s (cache hit) |
| train | ~2 min |
| evaluate | ~2 min |
| dashboard startup | ~5 s |

---

## Optional: LLM extraction (Groq)

The description feature cache (`data/processed/llm_features_cache.json`, 5,475 entries) and
duration cache (`data/processed/llm_duration_cache.json`, 5,541 entries) are included.
Features and training work without a Groq key.

To extend or refresh either cache:

```bash
# 1. Store your Groq API key (gitignored)
echo "gsk_YOUR_KEY_HERE" > .secrets/groq.key

# 2. Fill / extend the feature cache (~2 notes/sec, resume-safe)
python -m src.llm_extract

# 3. Fill / extend the duration estimate cache (separate run)
python -m src.llm_extract --duration

# 4. Re-run features and retrain after cache update
python -m src.features
python -m src.train
```

---

## Optional: EDA notebook

```bash
jupyter notebook notebooks/01_eda.ipynb
```

Pre-rendered HTML is at `reports/01_eda.html` — no Jupyter needed to view the EDA.

---

## Reproducing the pitch deck

```bash
npm install pptxgenjs --save-dev
node build_deck.js
# Output: reports/GridLock_PS2_Pitch.pptx
```

---

## File layout

```
grid_lock_phase_2/
├── data/
│   ├── raw/          # original CSV (unchanged)
│   └── processed/    # parquet + LLM caches
├── src/
│   ├── config.py     # paths, feature lists, banned-leakage list
│   ├── data_prep.py  # clean + impute + target derivation
│   ├── features.py   # 47 leakage-safe features
│   ├── llm_extract.py# Groq extraction + caching
│   ├── train.py      # 3 XGBoost models + bucket classifier
│   ├── evaluate.py   # metrics, SHAP, calibration
│   ├── predict.py    # single-incident inference
│   ├── recommend.py  # deployment plan rule engine
│   └── text_features.py  # rule-based fallback extractor
├── app/dashboard.py  # Streamlit demo
├── models/           # saved .joblib models + metrics.json
├── reports/
│   ├── REPORT.md     # written report
│   ├── figures/      # SHAP + calibration + EDA charts
│   └── GridLock_PS2_Pitch.pptx
├── notebooks/01_eda.ipynb
├── requirements.txt
└── INSTRUCTIONS_TO_RUN.md  # this file
```

---

## Troubleshooting

**`ModuleNotFoundError`** — run `pip install -r requirements.txt` in the repo root.

**`FileNotFoundError: incidents_clean.parquet`** — run `python -m src.data_prep` first.

**`FileNotFoundError: t1_closure.joblib`** — run `python -m src.train` first.

**Streamlit port conflict** — run `streamlit run app/dashboard.py --server.port 8502`.

**Groq rate limit** — `llm_extract` handles this with exponential back-off; re-run to resume from where it left off (resume-safe).
