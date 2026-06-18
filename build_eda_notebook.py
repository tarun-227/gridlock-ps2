"""Builds notebooks/01_eda.ipynb (narrative + inline tables/figures) and executes it."""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
from nbconvert.preprocessors import ExecutePreprocessor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "notebooks" / "01_eda.ipynb"

md = new_markdown_cell
code = new_code_cell
cells = []

cells.append(md(
    "# PS2 — Event-Driven Congestion · Exploratory Data Analysis\n"
    "**Flipkart × Bengaluru Traffic Police.** This notebook explores the provided incident "
    "dataset only (no external data) to ground the modelling of three targets — "
    "`requires_road_closure` (T1), `priority` (T2) and `resolution_time` (T3) — and surfaces "
    "the three data findings that shaped every downstream decision:\n"
    "1. **End-point coordinates leak the closure label** (recorded *because* a closure happened).\n"
    "2. **Priority is a deterministic function of corridor** — a rule, not a prediction.\n"
    "3. **Resolution time is partly a recording artifact** + a multi-week civic-process tail.\n"))

cells.append(code(
    "import sys, os\n"
    f"sys.path.insert(0, r'{ROOT}')\n"
    "os.environ.setdefault('PYTHONBREAKPOINT','0')\n"
    "import numpy as np, pandas as pd\n"
    "from IPython.display import Image\n"
    "from src import eda, config as C\n"
    "raw, df = eda.load()\n"
    "paths = eda.generate_all()   # (re)generate all figures into reports/figures/eda\n"
    "print('rows:', len(df), '| columns:', raw.shape[1])\n"
    "print('period:', df['start_datetime'].min().date(), '->', df['start_datetime'].max().date())"))

cells.append(md("## 1. Overview & data quality\n"
                "46 columns, ~8.2k incidents over ~5 months. Many columns are ≈100% null "
                "(bookkeeping) and are dropped; the modelling uses the populated, at-report-time fields."))
cells.append(code(
    "nr = (raw.isna().mean()*100).round(1).sort_values(ascending=False)\n"
    "display(nr.head(12).to_frame('pct_missing'))\n"
    "Image(str(C.FIGURES_DIR/'eda'/'01_null_rates.png'))"))

cells.append(md("## 2. Prediction targets\n"
                "T1 is **imbalanced** (~8% closures). T2 is ~62% High. T3 (resolution minutes) is "
                "**heavy-tailed** — and, critically, for the dominant breakdown class it clusters at "
                "~135 min (records auto-modified ~2h after start, not a real clearance signal)."))
cells.append(code(
    "print('T1 closure %:', round(df[C.T1].mean()*100,1))\n"
    "print('T2 High %   :', round(df[C.T2].mean()*100,1))\n"
    "display(Image(str(C.FIGURES_DIR/'eda'/'02_target_distributions.png')))\n"
    "Image(str(C.FIGURES_DIR/'eda'/'03_breakdown_artifact.png'))"))

cells.append(md("## 3. What drives a road closure?\n"
                "Closure is overwhelmingly **event-driven**: VIP movement, public events, protests, "
                "tree-fall and construction close roads far more than breakdowns/accidents. "
                "**Planned events** close roads ~5× as often as unplanned — exactly the PS focus."))
cells.append(code(
    "cr = df.groupby('event_cause_norm')['rc'].mean().sort_values(ascending=False)\n"
    "display(cr.head(10).to_frame('closure_rate').round(3))\n"
    "Image(str(C.FIGURES_DIR/'eda'/'04_closure_drivers.png'))"))

cells.append(md("## 4. Temporal patterns\n"
                "Closure risk spikes in the **evening (16–19h)** and around **midday (11–12h)**; the "
                "naive 7–10/17–20 peak window is ~flat, so we use a refined peak definition. "
                "Monthly closure rate trends upward across the window."))
cells.append(code("Image(str(C.FIGURES_DIR/'eda'/'05_temporal.png'))"))

cells.append(md("## 5. Spatial structure\n"
                "Clean Bengaluru bounding box, no null coordinates → internal spatial features "
                "(~1 km hotspot grid, distance-to-centroid) are viable without any external data. "
                "A handful of locations recur heavily (e.g. ORR-Marathahalli)."))
cells.append(code(
    "display(df['address'].value_counts().head(5).to_frame('incidents'))\n"
    "Image(str(C.FIGURES_DIR/'eda'/'06_spatial.png'))"))

cells.append(md("## 6. ⚠️ Headline audit — leakage, determinism & the artifact\n"
                "These three findings are *the* differentiator: they prevent a hollow 0.98-F1 model "
                "and dictate honest evaluation."))
cells.append(code(
    "has_end = (df['endlatitude'].fillna(0)!=0).astype(int)\n"
    "print('End-point present vs closure (LEAKAGE):')\n"
    "display(pd.crosstab(has_end, df[C.T1], rownames=['has_end_point'], colnames=['closure']))\n"
    "mixed = df.groupby('corridor')[C.T2].mean()\n"
    "print('Corridors that are NOT ~pure High/Low (priority determinism):',\n"
    "      int(((mixed>0.02)&(mixed<0.98)).sum()), 'of', mixed.size)\n"
    "Image(str(C.FIGURES_DIR/'eda'/'07_leakage_determinism_audit.png'))"))

cells.append(md("## 7. Free-text officer notes\n"
                "~83% of incidents carry a short note (English/Kanglish ~87%, Kannada ~13%). These "
                "are mined into structured features (severity, lane-blocking, tow-needed, subtype) "
                "via a local multilingual LLM (qwen2.5:3b) with a fast rule-based fallback."))
cells.append(code("Image(str(C.FIGURES_DIR/'eda'/'08_text_keywords.png'))"))

cells.append(md("## 8. Takeaways → modelling\n"
                "- **T1**: learnable; ban end-point features; key signals = event_cause, is_planned, "
                "corridor recurrence, LLM severity. Use PR-AUC + calibrated probabilities.\n"
                "- **T2**: present honestly as the corridor rule (+ a corridor-blind sanity model).\n"
                "- **T3**: artifact-limited; use AFT survival (uses censored 'active' incidents) for "
                "ranking + a 6h-capped regressor for point estimates; report robust metrics and the "
                "data-quality recommendation.\n"
                "- **Splitting**: strictly chronological; recurrence features are past-only."))

nb = new_notebook(cells=cells, metadata={"kernelspec": {
    "name": "python3", "display_name": "Python 3", "language": "python"}})

ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
ep.preprocess(nb, {"metadata": {"path": str(ROOT / "notebooks")}})
nbf.write(nb, str(OUT))
print("wrote + executed", OUT)
