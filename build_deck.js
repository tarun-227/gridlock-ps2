const pptxgen = require("pptxgenjs");

// ── Palette ─────────────────────────────────────────────────────────────────
const NAVY    = "0D1B3E";   // dark bg
const TEAL    = "00C2A8";   // accent / numbers
const ICE     = "C8DEFF";   // body text on dark
const LIGHT   = "F2F6FC";   // content slide bg
const MID     = "1A3A6C";   // card bg on light slides
const WHITE   = "FFFFFF";
const DARKTEXT= "0D1B3E";
const SUBTEXT = "4A6080";
const AMBER   = "FFAA00";   // warning highlight

// ── Helpers ──────────────────────────────────────────────────────────────────
function makeShadow() {
  return { type: "outer", color: "000000", opacity: 0.12, blur: 8, offset: 3, angle: 135 };
}

function darkSlide(pres) {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  return s;
}

function lightSlide(pres) {
  const s = pres.addSlide();
  s.background = { color: LIGHT };
  // top accent bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: TEAL }, line: { color: TEAL } });
  return s;
}

function slideTitle(s, text, y = 0.22) {
  s.addText(text, {
    x: 0.45, y, w: 9.1, h: 0.55,
    fontSize: 26, bold: true, color: DARKTEXT, fontFace: "Calibri", margin: 0,
  });
}

function subheading(s, text, x, y, w, color = SUBTEXT) {
  s.addText(text, { x, y, w, h: 0.3, fontSize: 11, bold: true, color, fontFace: "Calibri",
    charSpacing: 1, margin: 0 });
}

function tealAccent(s, x, y, h = 0.9) {
  s.addShape(s.pres?.shapes?.RECTANGLE || "rect", { x, y, w: 0.055, h,
    fill: { color: TEAL }, line: { color: TEAL } });
}

function card(s, pres, x, y, w, h, fillColor = WHITE) {
  s.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: fillColor }, line: { color: "D8E4F0", width: 0.5 },
    shadow: makeShadow(),
  });
}

function bigStat(s, num, label, x, y, numColor = TEAL) {
  s.addText(num,   { x, y,       w: 2.4, h: 0.65, fontSize: 40, bold: true, color: numColor, fontFace: "Calibri", align: "center", margin: 0 });
  const ly = y + 0.6; s.addText(label, { x, y: ly, w: 2.4, h: 0.3,  fontSize: 10, color: SUBTEXT, fontFace: "Calibri", align: "center", margin: 0 });
}

// ── Slides ───────────────────────────────────────────────────────────────────

let pres = new pptxgen();
pres.layout  = "LAYOUT_16x9";
pres.author  = "PS2 Team";
pres.title   = "GridLock: Event-Driven Congestion Forecasting";

// ── SLIDE 1 — Title (dark) ───────────────────────────────────────────────────
{
  const s = darkSlide(pres);

  // left accent bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.35, h: 5.625, fill: { color: TEAL }, line: { color: TEAL } });

  s.addText("GridLock", {
    x: 0.65, y: 1.05, w: 8.8, h: 1.1,
    fontSize: 60, bold: true, color: WHITE, fontFace: "Calibri", margin: 0,
  });
  s.addText("Event-Driven Congestion Forecasting", {
    x: 0.65, y: 2.1, w: 8.8, h: 0.55,
    fontSize: 24, bold: false, color: TEAL, fontFace: "Calibri", margin: 0,
  });
  s.addText("PS2  ·  Flipkart × Bengaluru Traffic Police", {
    x: 0.65, y: 2.72, w: 8.8, h: 0.35,
    fontSize: 14, color: ICE, fontFace: "Calibri", margin: 0,
  });

  // divider
  s.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 3.2, w: 5.5, h: 0.04, fill: { color: "2A4A80" }, line: { color: "2A4A80" } });

  s.addText("Prototype Round 2 Submission", {
    x: 0.65, y: 3.35, w: 8.8, h: 0.3,
    fontSize: 12, color: "6A90C0", fontFace: "Calibri", italic: true, margin: 0,
  });

  // 3 quick stats bottom
  const stats = [["8,171", "Incidents analysed"], ["47", "Leakage-safe features"], ["3", "Prediction targets"]];
  stats.forEach(([n, l], i) => {
    const bx = 0.65 + i * 3.05;
    s.addShape(pres.shapes.RECTANGLE, { x: bx, y: 4.35, w: 2.7, h: 0.88,
      fill: { color: "132654" }, line: { color: "1E3A7A" }, shadow: makeShadow() });
    s.addText(n, { x: bx, y: 4.42, w: 2.7, h: 0.42, fontSize: 26, bold: true, color: TEAL,
      fontFace: "Calibri", align: "center", margin: 0 });
    s.addText(l, { x: bx, y: 4.84, w: 2.7, h: 0.28, fontSize: 9, color: ICE,
      fontFace: "Calibri", align: "center", margin: 0 });
  });
}

// ── SLIDE 2 — The Problem (dark) ─────────────────────────────────────────────
{
  const s = darkSlide(pres);
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: AMBER }, line: { color: AMBER } });

  s.addText("THE PROBLEM", { x: 0.5, y: 0.18, w: 9, h: 0.28, fontSize: 10, bold: true,
    color: AMBER, fontFace: "Calibri", charSpacing: 3, margin: 0 });
  s.addText("Bengaluru loses hours to reactive traffic management", {
    x: 0.5, y: 0.5, w: 9, h: 0.75,
    fontSize: 28, bold: true, color: WHITE, fontFace: "Calibri", margin: 0,
  });

  const bullets = [
    ["🚦", "8,171 incidents (Nov 2023–Apr 2024)", "Rallies, VIP movement, construction, breakdowns across 22 corridors"],
    ["📋", "Deployment is experience-driven, not data-driven", "Officers decide resource allocation without any quantified impact estimate"],
    ["⏰", "Impact is unknown until the jam forms", "A tree-fall or planned rally is not quantified until it has already disrupted traffic"],
    ["🆘", "No decision support at report time", "Officers on the ground receive the call with no forecast, no recommended action"],
  ];
  bullets.forEach(([icon, head, sub], i) => {
    const by = 1.45 + i * 0.95;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: by, w: 9.1, h: 0.82,
      fill: { color: "132654" }, line: { color: "1E3A7A" }, shadow: makeShadow() });
    s.addText(icon, { x: 0.55, y: by + 0.1, w: 0.5, h: 0.5, fontSize: 18, align: "center", margin: 0 });
    s.addText(head, { x: 1.1, y: by + 0.07, w: 8.1, h: 0.3, fontSize: 13, bold: true, color: WHITE,
      fontFace: "Calibri", margin: 0 });
    s.addText(sub,  { x: 1.1, y: by + 0.38, w: 8.1, h: 0.26, fontSize: 10, color: ICE,
      fontFace: "Calibri", margin: 0 });
  });
}

// ── SLIDE 3 — Solution (light) ───────────────────────────────────────────────
{
  const s = lightSlide(pres);
  slideTitle(s, "Predict impact the moment an incident is reported");

  const cols = [
    { label: "T1  ROAD CLOSURE RISK", q: "Will this close the road?", stat: "3.74×", sub: "PR-AUC lift vs. baseline", detail: "XGBoost + isotonic calibration\n100% planned-event recall\nCalibrated probabilities" },
    { label: "T2  DISPATCH PRIORITY", q: "High or Low priority?",    stat: "0.916", sub: "corridor-blind F1", detail: "Rule-validated + corridor-blind\nWorks on any road, not just\ndesignated corridors" },
    { label: "T3  DURATION BUCKET",   q: "How long to clear?",       stat: "65.8%", sub: "bucket accuracy (vs 57.9%)", detail: "<1h · 1-3h · 3-8h · >8h\nLLM estimates clearance from\nofficer note directly" },
  ];

  cols.forEach((c, i) => {
    const cx = 0.3 + i * 3.22;
    card(s, pres, cx, 1.0, 3.0, 3.6);
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.0, w: 3.0, h: 0.36,
      fill: { color: MID }, line: { color: MID } });
    s.addText(c.label, { x: cx + 0.1, y: 1.05, w: 2.8, h: 0.28, fontSize: 9, bold: true,
      color: TEAL, fontFace: "Calibri", charSpacing: 1, margin: 0 });
    s.addText(c.q, { x: cx + 0.1, y: 1.44, w: 2.8, h: 0.42, fontSize: 14, bold: true,
      color: DARKTEXT, fontFace: "Calibri", margin: 0 });
    s.addText(c.stat, { x: cx + 0.1, y: 1.92, w: 2.8, h: 0.65, fontSize: 38, bold: true,
      color: TEAL, fontFace: "Calibri", align: "center", margin: 0 });
    s.addText(c.sub, { x: cx + 0.1, y: 2.55, w: 2.8, h: 0.25, fontSize: 9.5, color: SUBTEXT,
      fontFace: "Calibri", align: "center", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: cx + 0.1, y: 2.85, w: 2.8, h: 0.04,
      fill: { color: "D8E4F0" }, line: { color: "D8E4F0" } });
    s.addText(c.detail, { x: cx + 0.12, y: 2.96, w: 2.78, h: 0.56, fontSize: 9, color: SUBTEXT,
      fontFace: "Calibri", margin: 0 });
  });

  // bottom arrow note
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 4.72, w: 9.4, h: 0.54,
    fill: { color: "1A3A6C" }, line: { color: "1A3A6C" }, shadow: makeShadow() });
  s.addText("→  Recommendation engine maps predictions to: manpower count · barricade count · diversion route · alert level · tow dispatch", {
    x: 0.45, y: 4.82, w: 9.1, h: 0.32, fontSize: 11, bold: true, color: WHITE,
    fontFace: "Calibri", margin: 0,
  });
}

// ── SLIDE 4 — Data Insights (light) ─────────────────────────────────────────
{
  const s = lightSlide(pres);
  slideTitle(s, "Three findings that separate honest ML from a hollow demo");

  const insights = [
    {
      tag: "LEAKAGE TRAP", color: "C0392B",
      head: "End-point coordinates are a 98% proxy for closure",
      body: "Of 689 incidents with an end-point, 676 (98%) required closure. The end-point is recorded because a closure happened — not known at report time. A naive model scores F1 0.98 and is meaningless. We ban all end-point and resolution-time columns.",
    },
    {
      tag: "DETERMINISM", color: AMBER,
      head: "Priority is a rule, not a prediction",
      body: "priority = (corridor ≠ Non-corridor) with zero exceptions across 8,171 rows. We report this honestly and train a corridor-blind model (F1 0.916) that recovers priority from incident characteristics alone — enabling BTP to extend priority to any road.",
    },
    {
      tag: "ARTIFACT", color: "2980B9",
      head: "Resolution time is partly a recording artifact",
      body: "60% of records (vehicle_breakdown) are auto-modified at ~130 min regardless of real clearance. We re-frame T3 as bucket prediction (<1h / 1-3h / 3-8h / >8h) and identify which causes are predictable: accident=35 min MAE vs potholes=8,600 min.",
    },
  ];

  insights.forEach((ins, i) => {
    const by = 1.0 + i * 1.42;
    card(s, pres, 0.35, by, 9.3, 1.28);
    s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y: by, w: 0.055, h: 1.28,
      fill: { color: ins.color }, line: { color: ins.color } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: by + 0.08, w: 1.2, h: 0.26,
      fill: { color: ins.color }, line: { color: ins.color } });
    s.addText(ins.tag, { x: 0.54, y: by + 0.1, w: 1.12, h: 0.2, fontSize: 8, bold: true,
      color: WHITE, fontFace: "Calibri", charSpacing: 1, margin: 0 });
    s.addText("(" + ["a","b","c"][i] + ")", { x: 1.78, y: by + 0.1, w: 0.3, h: 0.22,
      fontSize: 11, bold: true, color: ins.color, fontFace: "Calibri", margin: 0 });
    s.addText(ins.head, { x: 0.5, y: by + 0.38, w: 8.9, h: 0.32, fontSize: 13, bold: true,
      color: DARKTEXT, fontFace: "Calibri", margin: 0 });
    s.addText(ins.body, { x: 0.5, y: by + 0.72, w: 8.9, h: 0.46, fontSize: 9.5, color: SUBTEXT,
      fontFace: "Calibri", margin: 0 });
  });
}

// ── SLIDE 5 — Feature Engineering (light) ────────────────────────────────────
{
  const s = lightSlide(pres);
  slideTitle(s, "47 leakage-safe features — all computable at report time");

  const groups = [
    { icon: "🕐", label: "Temporal", detail: "Hour, day-of-week, month\nRefined peak: 11-12h & 16-19h\nWeekend flag, night flag, hour bucket" },
    { icon: "📈", label: "Past-only recurrence", detail: "Corridor / zone / grid / cause / veh-type\nclosure rates & incident counts\nDays-since-last, city load (24h)" },
    { icon: "✖", label: "Interaction features", detail: "planned_cause_risk = is_planned × cause_closure_rate\npeak_cause_risk = is_peak × cause_closure_rate\ncorridor_cause_risk (product)" },
    { icon: "🤖", label: "LLM text mining (Groq)", detail: "Severity 1-5 · lane blocking · vehicles\nTow/crane required · incident subtype\nEstimated clearance minutes" },
    { icon: "⏱", label: "Duration priors", detail: "Past-only mean clearance time\nPer cause, corridor, zone\nPast-only, no future leakage" },
    { icon: "📍", label: "Spatial & flags", detail: "Lat / lon / distance to centroid\nis_planned · is_heavy_vehicle\nis_non_corridor · zone_missing" },
  ];

  groups.forEach((g, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const gx = 0.3 + col * 3.18;
    const gy = 1.0 + row * 2.15;
    card(s, pres, gx, gy, 3.0, 1.95);
    s.addText(g.icon, { x: gx + 0.12, y: gy + 0.12, w: 0.45, h: 0.4, fontSize: 20,
      align: "center", margin: 0 });
    s.addText(g.label, { x: gx + 0.62, y: gy + 0.15, w: 2.28, h: 0.32, fontSize: 12,
      bold: true, color: DARKTEXT, fontFace: "Calibri", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: gx + 0.12, y: gy + 0.55, w: 2.76, h: 0.03,
      fill: { color: "D8E4F0" }, line: { color: "D8E4F0" } });
    s.addText(g.detail, { x: gx + 0.12, y: gy + 0.65, w: 2.76, h: 1.16, fontSize: 9,
      color: SUBTEXT, fontFace: "Calibri", margin: 0 });
  });
}

// ── SLIDE 6 — Results (dark) ─────────────────────────────────────────────────
{
  const s = darkSlide(pres);
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: TEAL }, line: { color: TEAL } });
  s.addText("RESULTS", { x: 0.5, y: 0.18, w: 9, h: 0.25, fontSize: 10, bold: true,
    color: TEAL, fontFace: "Calibri", charSpacing: 3, margin: 0 });
  s.addText("Held-out chronological test set  ·  n = 1,226 incidents", {
    x: 0.5, y: 0.46, w: 9, h: 0.38, fontSize: 22, bold: true, color: WHITE,
    fontFace: "Calibri", margin: 0,
  });

  // Big stats row
  const topStats = [
    ["3.74×", "PR-AUC lift (T1)", "0.374 vs 0.086 baseline"],
    ["0.836", "ROC-AUC (T1)", "strong discriminative power"],
    ["1.000", "Planned recall (T1)", "every planned closure caught"],
    ["65.8%", "Bucket accuracy (T3)", "vs 57.9% majority baseline"],
  ];
  topStats.forEach(([n, l, sub], i) => {
    const bx = 0.25 + i * 2.4;
    s.addShape(pres.shapes.RECTANGLE, { x: bx, y: 1.0, w: 2.25, h: 1.28,
      fill: { color: "132654" }, line: { color: "1E3A7A" }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: bx, y: 1.0, w: 2.25, h: 0.04,
      fill: { color: TEAL }, line: { color: TEAL } });
    s.addText(n, { x: bx, y: 1.1, w: 2.25, h: 0.55, fontSize: 32, bold: true, color: TEAL,
      fontFace: "Calibri", align: "center", margin: 0 });
    s.addText(l, { x: bx + 0.08, y: 1.65, w: 2.1, h: 0.2, fontSize: 9, bold: true, color: WHITE,
      fontFace: "Calibri", align: "center", margin: 0 });
    s.addText(sub, { x: bx + 0.08, y: 1.86, w: 2.1, h: 0.18, fontSize: 7.5, color: ICE,
      fontFace: "Calibri", align: "center", margin: 0 });
  });

  // Results table
  const hdr = ["Target", "Metric", "Model", "Baseline"];
  const rows = [
    ["T1  Closure", "PR-AUC", "0.374  (3.74× lift)", "0.086"],
    ["T1  Closure", "ROC-AUC", "0.812", "0.500"],
    ["T1  Closure", "Planned recall", "1.000", "—"],
    ["T1  Closure", "Unplanned recall", "0.532", "—"],
    ["T2  Priority", "Weighted F1", "0.9984", "0.9984 (rule)"],
    ["T2  Blind", "Corridor-blind F1", "0.916", "—"],
    ["T3  Bucket", "Accuracy", "65.8%", "57.9%"],
    ["T3  Bucket", "1-3h class F1", "0.800", "—"],
    ["T3  AFT", "C-index", "0.598", "0.500"],
  ];

  const colW = [1.55, 1.9, 2.1, 2.1];
  const tx = 0.25, ty = 2.42, th = 0.26;

  // header
  hdr.forEach((h, ci) => {
    const cx = tx + colW.slice(0,ci).reduce((a,b)=>a+b,0);
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: ty, w: colW[ci], h: th,
      fill: { color: MID }, line: { color: "1E3A7A" } });
    s.addText(h, { x: cx+0.06, y: ty+0.04, w: colW[ci]-0.06, h: th-0.04,
      fontSize: 8.5, bold: true, color: TEAL, fontFace: "Calibri", margin: 0 });
  });

  rows.forEach((row, ri) => {
    const ry = ty + th * (ri + 1);
    const rowBg = ri % 2 === 0 ? "0E2050" : "122868";
    row.forEach((cell, ci) => {
      const cx = tx + colW.slice(0,ci).reduce((a,b)=>a+b,0);
      s.addShape(pres.shapes.RECTANGLE, { x: cx, y: ry, w: colW[ci], h: th,
        fill: { color: rowBg }, line: { color: "1A3570" } });
      const isNum = ci >= 2 && cell !== "—";
      s.addText(cell, { x: cx+0.06, y: ry+0.04, w: colW[ci]-0.06, h: th-0.04,
        fontSize: 8, bold: isNum, color: isNum ? TEAL : ICE, fontFace: "Calibri", margin: 0 });
    });
  });
}

// ── SLIDE 7 — LLM Text Mining (light) ────────────────────────────────────────
{
  const s = lightSlide(pres);
  slideTitle(s, "Officer notes are the strongest single predictor");

  // left: feature list
  card(s, pres, 0.3, 1.0, 5.2, 4.2);
  subheading(s, "WHAT GROQ llama-3.1-8b-instant EXTRACTS", 0.45, 1.08, 5.0, MID);

  const feats = [
    ["Severity score",         "1 (minor) to 5 (road blocked)"],
    ["Blocking lanes",         "Does the note imply lane(s) blocked?"],
    ["Vehicles involved",      "Count of vehicles mentioned"],
    ["Requires tow / crane",   "Recovery equipment needed?"],
    ["Incident subtype",       "vehicle_breakdown / collision / vip / crowd …"],
    ["Estimated duration",     "LLM reasons: crane + truck → ~240 min"],
  ];
  feats.forEach(([name, desc], i) => {
    const fy = 1.5 + i * 0.55;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: fy + 0.06, w: 0.22, h: 0.22,
      fill: { color: TEAL }, line: { color: TEAL } });
    s.addText(name, { x: 0.68, y: fy + 0.04, w: 4.66, h: 0.22, fontSize: 11, bold: true,
      color: DARKTEXT, fontFace: "Calibri", margin: 0 });
    s.addText(desc, { x: 0.68, y: fy + 0.26, w: 4.66, h: 0.2, fontSize: 9.5, color: SUBTEXT,
      fontFace: "Calibri", margin: 0 });
  });

  // right: stats + note
  card(s, pres, 5.65, 1.0, 4.05, 1.95);
  s.addText("5,541", { x: 5.75, y: 1.08, w: 3.85, h: 0.72, fontSize: 48, bold: true, color: TEAL,
    fontFace: "Calibri", align: "center", margin: 0 });
  s.addText("unique descriptions processed", { x: 5.75, y: 1.76, w: 3.85, h: 0.26, fontSize: 10,
    color: SUBTEXT, fontFace: "Calibri", align: "center", margin: 0 });

  card(s, pres, 5.65, 3.1, 4.05, 0.82);
  s.addText("~3.5 notes/sec", { x: 5.75, y: 3.18, w: 3.85, h: 0.38, fontSize: 22, bold: true,
    color: DARKTEXT, fontFace: "Calibri", align: "center", margin: 0 });
  s.addText("Groq batched API · 4 concurrent workers", { x: 5.75, y: 3.54, w: 3.85, h: 0.25,
    fontSize: 9.5, color: SUBTEXT, fontFace: "Calibri", align: "center", margin: 0 });

  card(s, pres, 5.65, 4.06, 4.05, 1.14);
  const points = ["Handles English · Kanglish · Kannada script", "Rule-based fallback = 100% coverage", "#1 SHAP contributor for closure (T1)", "Multilingual — no translation needed"];
  const ptxt = points.map((p,i) => [
    { text: "✓  ", options: { bold: true, color: TEAL } },
    { text: p, options: { color: SUBTEXT } },
    ...(i < points.length-1 ? [{ text: "\n", options: {} }] : []),
  ]).flat();
  s.addText(ptxt, { x: 5.78, y: 4.14, w: 3.82, h: 1.0, fontSize: 9.5, fontFace: "Calibri", margin: 0 });
}

// ── SLIDE 8 — Recommendation Engine (light) ──────────────────────────────────
{
  const s = lightSlide(pres);
  slideTitle(s, "From prediction to deployment plan in one call");

  // Example output box (left)
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 1.0, w: 4.4, h: 3.9,
    fill: { color: NAVY }, line: { color: TEAL, width: 1.5 }, shadow: makeShadow() });
  s.addText("EXAMPLE OUTPUT", { x: 0.45, y: 1.1, w: 4.1, h: 0.24, fontSize: 8, bold: true,
    color: TEAL, fontFace: "Calibri", charSpacing: 2, margin: 0 });
  s.addText("Tree fall · Tumkur Road · 18:30", { x: 0.45, y: 1.38, w: 4.1, h: 0.28,
    fontSize: 11, color: ICE, fontFace: "Calibri", italic: true, margin: 0 });

  const lines = [
    { icon: "🔴", label: "CRITICAL", val: "Alert level", color: "E74C3C" },
    { icon: "👮", label: "11 officers", val: "Deploy", color: TEAL },
    { icon: "🚧", label: "11 barricades", val: "Set up", color: TEAL },
    { icon: "↪️", label: "West of Chord Road", val: "Divert to", color: AMBER },
    { icon: "🏗️", label: "Dispatch crane", val: "Tow flag from note", color: TEAL },
    { icon: "⏱", label: "1-3h bucket", val: "Duration estimate", color: ICE },
  ];
  lines.forEach((l, i) => {
    const ly = 1.78 + i * 0.52;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.38, y: ly, w: 4.24, h: 0.44,
      fill: { color: i===0 ? "1a0a0a" : "132654" }, line: { color: "1E3A7A" } });
    s.addText(l.icon, { x: 0.42, y: ly+0.06, w: 0.4, h: 0.32, fontSize: 14, align: "center", margin: 0 });
    s.addText(l.val,   { x: 0.86, y: ly+0.06, w: 1.7, h: 0.2, fontSize: 8, color: "5A80B0",
      fontFace: "Calibri", margin: 0 });
    s.addText(l.label, { x: 0.86, y: ly+0.22, w: 3.62, h: 0.2, fontSize: 11, bold: true,
      color: l.color, fontFace: "Calibri", margin: 0 });
  });

  // right: formula cards
  const formulas = [
    { t: "MANPOWER (2–16 officers)", b: "base(priority)  +  closure_risk × 6  +  severity  +  peak_hour  +  chronic_corridor  +  planned_event  +  lanes_blocked" },
    { t: "BARRICADING (0–12)", b: "Triggered: closure_prob ≥ 0.4  OR  severity ≥ 4  OR  lanes_blocked\nCount = closure_prob × 8 + severity  +  2 (if blocking)" },
    { t: "DIVERSION ROUTE", b: "Named corridor → alternate from dataset-derived corridor families:\nTumkur Rd → West of Chord  ·  Mysore Rd → Magadi Rd  ·  Hosur Rd → Bannerghatta Rd" },
    { t: "ALERT LEVEL", b: "CRITICAL: prob ≥ 0.6 or severity 5\nHIGH: prob ≥ 0.35 or severity 4\nMEDIUM: prob ≥ 0.15 or severity 3   LOW: otherwise" },
  ];
  formulas.forEach((f, i) => {
    const fy = 1.0 + i * 1.12;
    card(s, pres, 4.88, fy, 4.82, 1.0);
    s.addShape(pres.shapes.RECTANGLE, { x: 4.88, y: fy, w: 0.055, h: 1.0,
      fill: { color: TEAL }, line: { color: TEAL } });
    s.addText(f.t, { x: 5.0, y: fy + 0.08, w: 4.6, h: 0.24, fontSize: 9.5, bold: true,
      color: DARKTEXT, fontFace: "Calibri", margin: 0 });
    s.addText(f.b, { x: 5.0, y: fy + 0.35, w: 4.6, h: 0.56, fontSize: 8.5, color: SUBTEXT,
      fontFace: "Calibri", margin: 0 });
  });
}

// ── SLIDE 9 — Post-Event Learning (light) ────────────────────────────────────
{
  const s = lightSlide(pres);
  slideTitle(s, "The system improves with every closed incident");

  // pipeline flow diagram
  const steps = ["New incident\nreported", "T1 / T2 / T3\npredicted", "Deployment\nrecommended", "Incident\ncloses", "Features\nupdated", "Model\nretrained"];
  const stepW = 1.38, gap = 0.2, startX = 0.3, stepY = 1.1, stepH = 0.9;
  steps.forEach((step, i) => {
    const sx = startX + i * (stepW + gap);
    const isLoop = i >= 3;
    s.addShape(pres.shapes.RECTANGLE, { x: sx, y: stepY, w: stepW, h: stepH,
      fill: { color: isLoop ? "1A3A6C" : TEAL }, line: { color: isLoop ? "1A3A6C" : TEAL } });
    s.addText(step, { x: sx + 0.04, y: stepY + 0.12, w: stepW - 0.08, h: stepH - 0.14,
      fontSize: 9.5, bold: true, color: WHITE, fontFace: "Calibri", align: "center", margin: 0 });
    if (i < steps.length - 1) {
      const ax = sx + stepW;
      s.addShape(pres.shapes.RECTANGLE, { x: ax, y: stepY + 0.4, w: gap, h: 0.08,
        fill: { color: DARKTEXT }, line: { color: DARKTEXT } });
    }
  });
  s.addText("← LEARNING LOOP", { x: startX + 3 * (stepW + gap), y: stepY + stepH + 0.08, w: 3*(stepW+gap), h: 0.24,
    fontSize: 8.5, bold: true, color: TEAL, fontFace: "Calibri", align: "center", charSpacing: 1, margin: 0 });

  const bullets = [
    { icon: "✅", head: "Zero re-engineering needed", body: "Recurrence features are past-only — re-running features → train on updated data automatically incorporates every new closed incident." },
    { icon: "💡", head: "Corridor-blind T2 enables expansion", body: "F1 0.916 from incident characteristics alone. BTP can assign priority to new roads not yet classified as formal corridors." },
    { icon: "⚠️", head: "Data quality finding for BTP", body: "Capturing a true 'road cleared' timestamp (not auto-modified record time) is the single biggest improvement BTP can make to unlock T3 accuracy." },
    { icon: "📡", head: "LLM cache grows incrementally", body: "New officer note patterns improve duration estimates over time. Resume-safe — no re-processing needed for existing descriptions." },
  ];
  bullets.forEach((b, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const bx = 0.3 + col * 4.85, by = 2.3 + row * 1.4;
    card(s, pres, bx, by, 4.65, 1.25);
    s.addText(b.icon, { x: bx + 0.12, y: by + 0.14, w: 0.45, h: 0.45, fontSize: 20, align: "center", margin: 0 });
    s.addText(b.head, { x: bx + 0.62, y: by + 0.14, w: 3.88, h: 0.3, fontSize: 11.5, bold: true,
      color: DARKTEXT, fontFace: "Calibri", margin: 0 });
    s.addText(b.body, { x: bx + 0.62, y: by + 0.46, w: 3.88, h: 0.66, fontSize: 9, color: SUBTEXT,
      fontFace: "Calibri", margin: 0 });
  });
}

// ── SLIDE 10 — Try It (dark) ─────────────────────────────────────────────────
{
  const s = darkSlide(pres);
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: TEAL }, line: { color: TEAL } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.35, h: 5.625, fill: { color: TEAL }, line: { color: TEAL } });

  s.addText("LIVE DEMO +\nREPRODUCIBLE PIPELINE", {
    x: 0.65, y: 0.45, w: 8.9, h: 1.15,
    fontSize: 36, bold: true, color: WHITE, fontFace: "Calibri", margin: 0,
  });

  const panels = [
    {
      title: "🔮  Predict & Recommend tab",
      items: [
        "Enter: corridor, cause, vehicle type, datetime, officer note",
        "Output: closure probability · priority · duration bucket",
        "Deployment plan: officers · barricades · diversion route",
        "Per-incident SHAP: why this forecast was made",
      ],
    },
    {
      title: "📊  Insights tab",
      items: [
        "Closure rate by cause / hour / corridor",
        "Model metrics vs baselines (all 3 targets)",
        "SHAP bar charts + calibration curve",
        "The three data findings explained",
      ],
    },
  ];
  panels.forEach((p, i) => {
    const px = 0.65 + i * 4.7;
    s.addShape(pres.shapes.RECTANGLE, { x: px, y: 1.75, w: 4.45, h: 2.65,
      fill: { color: "132654" }, line: { color: "1E3A7A" }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: px, y: 1.75, w: 4.45, h: 0.04,
      fill: { color: TEAL }, line: { color: TEAL } });
    s.addText(p.title, { x: px+0.15, y: 1.82, w: 4.15, h: 0.32, fontSize: 12, bold: true,
      color: WHITE, fontFace: "Calibri", margin: 0 });
    const btxt = p.items.map((item, j) => [
      { text: "› ", options: { color: TEAL, bold: true } },
      { text: item, options: { color: ICE } },
      ...(j < p.items.length-1 ? [{ text: "\n", options: {} }] : []),
    ]).flat();
    s.addText(btxt, { x: px+0.15, y: 2.22, w: 4.15, h: 2.0, fontSize: 10,
      fontFace: "Calibri", lineSpacingMultiple: 1.4, margin: 0 });
  });

  // run instructions
  s.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 4.56, w: 9.0, h: 0.75,
    fill: { color: "0A1428" }, line: { color: "1E3A7A" } });
  s.addText(
    "pip install -r requirements.txt  →  python -m src.data_prep  →  python -m src.features  →  python -m src.train  →  streamlit run app/dashboard.py",
    { x: 0.8, y: 4.67, w: 8.7, h: 0.52, fontSize: 9.5, color: TEAL, fontFace: "Consolas",
      align: "center", margin: 0 });
}

// ── Write ─────────────────────────────────────────────────────────────────────
const out = "C:\\Users\\user\\grid_lock_phase_2\\reports\\GridLock_PS2_Pitch.pptx";
pres.writeFile({ fileName: out }).then(() => console.log("Written:", out));
