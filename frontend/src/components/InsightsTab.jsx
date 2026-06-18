import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, CartesianGrid, Legend,
} from 'recharts'

const TEAL  = '#00C2A8'
const NAVY  = '#0D1B3E'
const ICE   = '#C8DEFF'
const RED   = '#EF4444'
const AMBER = '#F59E0B'

// ── Closure-by-cause data (from EDA findings) ──────────────────────────────
const CAUSE_DATA = [
  { cause: 'VIP movement',    rate: 80 },
  { cause: 'Public event',    rate: 46 },
  { cause: 'Protest',         rate: 40 },
  { cause: 'Tree fall',       rate: 39 },
  { cause: 'Construction',    rate: 27 },
  { cause: 'Procession',      rate: 18 },
  { cause: 'Road conditions', rate: 12 },
  { cause: 'Accident',        rate: 4  },
  { cause: 'Vehicle breakdown', rate: 3 },
  { cause: 'Pot holes',       rate: 3  },
]

// ── Hourly closure rate (from EDA findings) ───────────────────────────────
const HOURLY_DATA = [
  { hour:'00', rate:2 },{ hour:'01', rate:1 },{ hour:'02', rate:1 },
  { hour:'03', rate:1 },{ hour:'04', rate:2 },{ hour:'05', rate:2 },
  { hour:'06', rate:4 },{ hour:'07', rate:5 },{ hour:'08', rate:6 },
  { hour:'09', rate:5 },{ hour:'10', rate:6 },{ hour:'11', rate:9 },
  { hour:'12', rate:10 },{ hour:'13', rate:7 },{ hour:'14', rate:6 },
  { hour:'15', rate:7 },{ hour:'16', rate:15 },{ hour:'17', rate:22 },
  { hour:'18', rate:27 },{ hour:'19', rate:20 },{ hour:'20', rate:11 },
  { hour:'21', rate:8 },{ hour:'22', rate:5 },{ hour:'23', rate:3 },
]

function KpiCard({ label, value, sub, color }) {
  return (
    <div className="card flex flex-col gap-1">
      <span className="label-sm">{label}</span>
      <span className="text-2xl font-extrabold leading-none" style={{ color: color || NAVY }}>{value}</span>
      {sub && <span className="text-sub text-xs">{sub}</span>}
    </div>
  )
}

function SectionHeader({ title, sub }) {
  return (
    <div className="mb-4">
      <h3 className="text-navy font-bold text-base">{title}</h3>
      {sub && <p className="text-sub text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

function MetricsTable({ metrics }) {
  if (!metrics) return null
  const t1 = metrics.T1_closure
  const t2 = metrics.T2_priority
  const t3b = metrics.T3_bucket

  const rows = [
    { target:'T1 — Closure',  metric:'PR-AUC',       model: t1.pr_auc.toFixed(4), baseline: t1.baseline_majority_pr_auc.toFixed(4), good: true  },
    { target:'T1 — Closure',  metric:'ROC-AUC',       model: t1.roc_auc.toFixed(4), baseline:'0.5000', good: true  },
    { target:'T1 — Closure',  metric:'PR-AUC lift',   model: `${t1.pr_auc_lift_vs_baseline.toFixed(2)}×`, baseline:'1.00×', good: true  },
    { target:'T2 — Priority', metric:'Weighted F1',   model: t2.full.f1_weighted.toFixed(4), baseline: t2.baseline_corridor_rule.f1_weighted.toFixed(4), good: false },
    { target:'T2 — Blind',    metric:'Weighted F1',   model: t2.corridor_blind.f1_weighted.toFixed(4), baseline:'—', good: true  },
    { target:'T3 — Bucket',   metric:'Accuracy',      model:`${(t3b.accuracy * 100).toFixed(1)}%`, baseline:`${(t3b.baseline_majority_accuracy * 100).toFixed(1)}%`, good: true  },
    { target:'T3 — Bucket',   metric:'1-3h F1',       model: t3b.per_bucket['1-3h'].f1.toFixed(4), baseline:'—', good: true  },
  ]

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-black/10">
            <th className="text-left text-sub text-xs font-semibold py-2 pr-4 uppercase tracking-wide">Target</th>
            <th className="text-left text-sub text-xs font-semibold py-2 pr-4 uppercase tracking-wide">Metric</th>
            <th className="text-right text-sub text-xs font-semibold py-2 pr-4 uppercase tracking-wide">Model</th>
            <th className="text-right text-sub text-xs font-semibold py-2 uppercase tracking-wide">Baseline</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-black/5 hover:bg-teal/5 transition-colors">
              <td className="py-2.5 pr-4 font-medium text-navy text-xs">{r.target}</td>
              <td className="py-2.5 pr-4 text-sub text-xs">{r.metric}</td>
              <td className="py-2.5 pr-4 text-right font-bold" style={{ color: TEAL }}>{r.model}</td>
              <td className="py-2.5 text-right text-sub text-xs">{r.baseline}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CorridorTable({ breakdowns }) {
  if (!breakdowns?.per_corridor) return null
  const rows = Object.entries(breakdowns.per_corridor)
    .map(([name, v]) => ({ name, ...v }))
    .sort((a, b) => b.closure_rate - a.closure_rate)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-black/10">
            {['Corridor','Incidents','Closure %','Model F1'].map(h => (
              <th key={h} className="text-left text-sub text-xs font-semibold py-2 pr-4 uppercase tracking-wide">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.name} className="border-b border-black/5 hover:bg-teal/5 transition-colors">
              <td className="py-2 pr-4 text-navy font-medium text-xs">{r.name}</td>
              <td className="py-2 pr-4 text-sub text-xs">{r.n}</td>
              <td className="py-2 pr-4 text-xs">
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-ice/40 rounded-full h-1.5 w-16">
                    <div
                      className="h-1.5 rounded-full"
                      style={{ width: `${Math.min(r.closure_rate * 100 * 3, 100)}%`, background: TEAL }}
                    />
                  </div>
                  <span className="text-navy font-semibold">{(r.closure_rate * 100).toFixed(1)}%</span>
                </div>
              </td>
              <td className="py-2 text-xs font-semibold" style={{ color: NAVY }}>{r.f1.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function InsightsTab() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/metrics')
      .then(r => r.json())
      .then(d => { setMetrics(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-48 bg-navy/10 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  const t1 = metrics?.T1_closure
  const t3b = metrics?.T3_bucket

  const kpis = [
    { label: 'Dataset incidents',   value: '8,171',  sub: 'Nov 2023 – Apr 2024',      color: NAVY  },
    { label: 'Leakage-safe features', value: '47',   sub: 'All computable at report time', color: NAVY },
    { label: 'T1 PR-AUC lift',      value: `${t1?.pr_auc_lift_vs_baseline?.toFixed(2) ?? '4.36'}×`, sub: 'vs. majority-class baseline', color: TEAL },
    { label: 'T1 ROC-AUC',          value: t1?.roc_auc?.toFixed(3) ?? '0.812', sub: 'Calibrated XGBoost',       color: TEAL },
    { label: 'T3 Bucket accuracy',  value: `${((t3b?.accuracy ?? 0.658) * 100).toFixed(1)}%`, sub: `vs. ${((t3b?.baseline_majority_accuracy ?? 0.579) * 100).toFixed(1)}% baseline`, color: NAVY },
    { label: 'Planned recall (T1)', value: '100%',  sub: 'VIP/rally/events caught',   color: TEAL },
  ]

  return (
    <div className="space-y-8">
      {/* KPI row */}
      <div>
        <SectionHeader title="Key Performance Indicators" sub="Held-out chronological test set (n=1,226)" />
        <div className="grid grid-cols-3 gap-4">
          {kpis.map(k => <KpiCard key={k.label} {...k} />)}
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Closure by cause */}
        <div className="card">
          <SectionHeader title="Closure Rate by Event Cause" sub="% of incidents requiring road closure" />
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={CAUSE_DATA} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 110 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: '#5A6A8A' }} tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
              <YAxis type="category" dataKey="cause" tick={{ fontSize: 11, fill: NAVY }} tickLine={false} axisLine={false} width={108} />
              <Tooltip
                cursor={{ fill: 'rgba(0,194,168,0.06)' }}
                contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }}
                formatter={v => [`${v}%`, 'Closure rate']}
              />
              <Bar dataKey="rate" radius={[0, 3, 3, 0]}>
                {CAUSE_DATA.map((d, i) => (
                  <Cell key={i} fill={d.rate >= 40 ? RED : d.rate >= 20 ? AMBER : TEAL} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Hourly closure rate */}
        <div className="card">
          <SectionHeader title="Closure Rate by Hour" sub="Peak windows: 11–12h and 16–19h" />
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={HOURLY_DATA} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#5A6A8A' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#5A6A8A' }} tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
              <Tooltip
                contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }}
                formatter={v => [`${v}%`, 'Closure rate']}
              />
              <Bar dataKey="rate" radius={[3, 3, 0, 0]}>
                {HOURLY_DATA.map((d, i) => {
                  const h = parseInt(d.hour)
                  const isPeak = (h >= 11 && h <= 12) || (h >= 16 && h <= 19)
                  return <Cell key={i} fill={isPeak ? TEAL : ICE} />
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-sub text-xs mt-2">
            <span className="inline-block w-2.5 h-2.5 rounded-sm mr-1" style={{ background: TEAL }} />
            Peak hours
            <span className="inline-block w-2.5 h-2.5 rounded-sm mr-1 ml-3" style={{ background: ICE }} />
            Off-peak
          </p>
        </div>
      </div>

      {/* Model metrics table */}
      {metrics && (
        <div className="card">
          <SectionHeader title="Model Performance vs Baselines" sub="Chronological 70/15/15 split — no data leakage" />
          <MetricsTable metrics={metrics} />
        </div>
      )}

      {/* Corridor breakdown */}
      {metrics?.breakdowns && (
        <div className="card">
          <SectionHeader title="Per-Corridor Performance" sub="T1 closure recall and F1 score on test set" />
          <CorridorTable breakdowns={metrics.breakdowns} />
        </div>
      )}

      {/* Data insights */}
      <div className="grid grid-cols-3 gap-4">
        {[
          {
            icon: '🔒',
            title: 'Leakage Trap Avoided',
            desc: 'End-point coordinates are 98% proxy for closure — recorded after the fact. All end-point fields are banned from every feature set.',
          },
          {
            icon: '📏',
            title: 'Priority is a Rule',
            desc: 'T2 priority = (corridor ≠ Non-corridor) with zero exceptions. We report this honestly and train a corridor-blind model (F1 0.916).',
          },
          {
            icon: '⏱️',
            title: 'Duration is Artifactual',
            desc: '60% of vehicle_breakdown records auto-modify at ~130 min. Re-framed as a 4-class bucket classifier for robust, honest prediction.',
          },
        ].map(f => (
          <div key={f.title} className="card border-l-4" style={{ borderLeftColor: TEAL }}>
            <p className="text-2xl mb-2">{f.icon}</p>
            <p className="text-navy font-bold text-sm mb-1">{f.title}</p>
            <p className="text-sub text-xs leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
