# Hackathon Submission Fields — PS2 Event-Driven Congestion

Copy-paste each field into the submission form.

---

## Title

```
GridLock: Event-Driven Congestion Forecasting & Resource Deployment for Bengaluru Traffic Police
```

---

## Theme

**Event-Driven Congestion** (PS2)

---

## Description (markdown)

```markdown
## Problem

Planned and unplanned events — rallies, VIP movement, construction, breakdowns, tree-fall —
cause localised traffic congestion across Bengaluru. Today, impact is **not quantified in
advance**: resource deployment (officers, barricades, diversions) is entirely experience-driven,
and dispatchers receive no decision support at the time an incident is reported.

## What We Built

**GridLock** is a decision-support system that, the moment a new incident is reported, predicts
its traffic impact across three targets and generates an explainable deployment plan:

| Target | Question | Model |
|---|---|---|
| **T1** Road closure risk | Will this need a closure? | XGBoost + isotonic calibration |
| **T2** Dispatch priority | High or Low? | XGBoost (+ corridor-blind variant) |
| **T3** Duration bucket | <1h / 1-3h / 3-8h / >8h? | XGBoost 4-class classifier |

The **recommendation engine** maps predictions to a concrete plan: officer count, barricade
count, diversion route, alert level, tow/crane dispatch — every number with a stated rationale.

## Three Findings That Shaped Everything

We don't claim a generic ML pipeline. Our EDA surfaced three data-specific findings:

1. **Leakage trap** — End-point coordinates are a 98% proxy for the closure label (recorded
   *because* a closure happened, not known at report time). A naive model scores F1 ≈ 0.98 and
   is meaningless. We ban all end-point and resolution-time columns from every model.

2. **Priority is a deterministic rule** — `priority = (corridor ≠ "Non-corridor")` with zero
   exceptions. We report this honestly and train a corridor-blind model (F1 0.916) that recovers
   priority from incident characteristics alone — enabling BTP to extend it to unlabelled roads.

3. **Resolution time is partly a recording artifact** — 60% of records (vehicle_breakdown) are
   auto-modified at ~130 min regardless of actual clearance. We re-frame T3 as bucket prediction
   and identify which causes are predictable (accidents, breakdowns) vs. not (potholes, road
   works).

## Key Results (held-out chronological test, n = 1,226)

| Metric | Value | vs Baseline |
|---|---|---|
| T1 PR-AUC | **0.374** | **3.74× lift** over majority (0.086) |
| T1 ROC-AUC | **0.812** | — |
| T1 Planned recall | **1.000** | every planned closure caught |
| T2 Corridor-blind F1 | **0.916** | — |
| T3 Bucket accuracy | **65.8%** | vs 57.9% majority baseline |
| T3 1–3h F1 | **0.800** | — |

## Feature Engineering (47 leakage-safe features)

All features are computable at report time (no post-hoc data):
- **Past-only recurrence rates** — corridor, zone, grid, cause, vehicle type, police station
  (cumulative via time-ordered `searchsorted`, strictly no future leakage)
- **Interaction features** — `planned_cause_risk = is_planned × cause_closure_rate` separates
  high-risk VIP/procession from low-risk construction without a two-level split
- **LLM text mining** — Groq `llama-3.1-8b-instant` extracts severity, lane blocking, tow
  required, incident subtype, and estimated clearance minutes from 5,541 officer notes.
  `llm_subtype_le` is the #1 SHAP contributor for T1. Rule-based fallback ensures 100% coverage.
- **Past-only duration priors** — mean clearance time per cause/corridor/zone (censored rows
  excluded), providing group-level duration context without leakage.

## Dataset Compliance

Uses **only** the provided PS2 dataset (8,171 incidents, Nov 2023–Apr 2024). The Groq LLM
processes existing `description` text already in the dataset — no external data is introduced.

## Post-Event Learning

Every closed incident automatically improves the system: past-only recurrence features
accumulate new history; re-running `features → train` incorporates it. The corridor-blind T2
model enables priority assignment to roads not yet formally designated as corridors.

## Run in 3 Commands

```bash
pip install -r requirements.txt
python -m src.train      # skip if using pre-built models
streamlit run app/dashboard.py
```
```

---

## Instructions to Run

See `INSTRUCTIONS_TO_RUN.md` in the repository root (also pasted below).

### Short version for the form:

```
Prerequisites: Python 3.9+, pip

Quick start (pre-built models included):
  git clone <repo-url> && cd grid_lock_phase_2
  pip install -r requirements.txt
  streamlit run app/dashboard.py
  → open http://localhost:8501

Full re-run from scratch:
  python -m src.data_prep   # clean raw CSV → parquet (~10s)
  python -m src.features    # build 47 leakage-safe features (~30s)
  python -m src.train       # train T1/T2/T3 models (~2 min)
  python -m src.evaluate    # metrics + SHAP figures (~2 min)
  streamlit run app/dashboard.py

Optional LLM extraction (Groq API key in .secrets/groq.key):
  python -m src.llm_extract           # feature cache (5,541 descriptions)
  python -m src.llm_extract --duration # duration estimate cache

EDA notebook: jupyter notebook notebooks/01_eda.ipynb
  (pre-rendered HTML at reports/01_eda.html, no Jupyter needed)

Dataset: place the original CSV at data/raw/ (unchanged from PS2 distribution)
```

---

## Video URL

*(Record a 2–5 min demo video showing: entering an incident in the dashboard → seeing
closure probability + recommendations → switching to Insights tab. Upload to YouTube/Drive
and paste URL here.)*

---

## Demo Link

*(Deploy the Streamlit app to Streamlit Cloud or HuggingFace Spaces and paste URL here.)*
Streamlit Cloud deploy command:
```
streamlit run app/dashboard.py
```
Note: set `GROQ_API_KEY` in Streamlit secrets if you want live LLM on new descriptions.

---

## Repository URL

*(Push to GitHub and paste URL here. Make sure the repo is public or shared with judges.)*

Suggested repo name: `gridlock-ps2` or `grid-lock-phase-2`

---

## Source Code (zip)

Create the zip with:
```bash
# From the project root — excludes .gitignore patterns and large cache files
python -c "
import zipfile, os, pathlib

ROOT = pathlib.Path('.')
EXCLUDE = {'.git', '__pycache__', '.secrets', 'node_modules', 'venv', '.venv',
           'llm_features_cache.json', 'llm_duration_cache.json'}

with zipfile.ZipFile('GridLock_PS2_Source.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in ROOT.rglob('*'):
        if f.is_file() and not any(ex in f.parts for ex in EXCLUDE):
            if not any(f.name.endswith(ext) for ext in ['.pyc', '.pptx', '.pdf']):
                zf.write(f, f.relative_to(ROOT))
print('Created GridLock_PS2_Source.zip')
"
```
Upload `GridLock_PS2_Source.zip`.

---

## Presentation

Upload `reports/GridLock_PS2_Pitch.pptx` (10 slides, ~350 KB).
```
