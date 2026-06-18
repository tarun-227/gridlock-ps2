"""Build shareable, self-contained HTML deliverables (open in browser / print to PDF):
  - reports/REPORT.html       (styled report + embedded key figures)
  - reports/01_eda.html       (the executed EDA notebook, images embedded)
"""
import base64
from pathlib import Path
import markdown
import nbformat
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"

CSS = """
<style>
body{font-family:Segoe UI,Arial,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;
  color:#1a1a1a;line-height:1.5}
h1,h2,h3{color:#0b3d5c} h1{border-bottom:3px solid #2b8cbe;padding-bottom:.3rem}
h2{border-bottom:1px solid #ddd;padding-bottom:.2rem;margin-top:2rem}
table{border-collapse:collapse;margin:1rem 0;width:100%} th,td{border:1px solid #ccc;padding:6px 10px}
th{background:#eef6fb} code{background:#f4f4f4;padding:1px 4px;border-radius:3px}
pre{background:#f7f7f7;padding:10px;border-radius:6px;overflow:auto}
img{max-width:100%;border:1px solid #eee;border-radius:6px;margin:.5rem 0}
.fig-cap{color:#555;font-size:.9em;margin-bottom:1.2rem}
blockquote{border-left:4px solid #e6550d;margin:0;padding-left:1rem;color:#444}
</style>
"""

KEY_FIGS = [
    ("figures/eda/07_leakage_determinism_audit.png",
     "Headline audit: end-point leakage, priority determinism, 500× resolution spread by cause"),
    ("figures/eda/04_closure_drivers.png", "Closure rate by cause; planned vs unplanned (5×)"),
    ("figures/eda/02_target_distributions.png", "Target distributions (T1 imbalanced, T3 heavy-tailed)"),
    ("figures/eda/03_breakdown_artifact.png", "Resolution-time recording artifact (~135 min spike)"),
    ("figures/t1_shap.png", "T1 closure — SHAP feature importance"),
    ("figures/t1_calibration.png", "T1 — probability calibration"),
    ("figures/eda/05_temporal.png", "Temporal closure patterns"),
    ("figures/eda/06_spatial.png", "Spatial distribution of incidents/closures"),
]


def _img_tag(rel, cap):
    p = REPORTS / rel
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b64}"/><div class="fig-cap">{cap}</div>'


def build_report_html():
    text = (REPORTS / "REPORT.md").read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    figs = "<h2>Figure appendix</h2>" + "".join(_img_tag(r, c) for r, c in KEY_FIGS)
    html = f"<!doctype html><html><head><meta charset='utf-8'>{CSS}</head><body>{body}{figs}</body></html>"
    out = REPORTS / "REPORT.html"
    out.write_text(html, encoding="utf-8")
    print("wrote", out)


def build_eda_html():
    nb = nbformat.read(str(ROOT / "notebooks" / "01_eda.ipynb"), as_version=4)
    exporter = HTMLExporter()
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    html, _ = exporter.from_notebook_node(nb)
    out = REPORTS / "01_eda.html"
    out.write_text(html, encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    build_report_html()
    build_eda_html()
