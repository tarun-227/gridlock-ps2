import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'

const ALERT_STYLES = {
  CRITICAL: { bg: 'bg-red-50',    border: 'border-red-400',    text: 'text-red-700',    badge: 'bg-red-500',    icon: '🚨' },
  HIGH:     { bg: 'bg-amber-50',  border: 'border-amber-400',  text: 'text-amber-700',  badge: 'bg-amber-500',  icon: '⚠️' },
  MEDIUM:   { bg: 'bg-yellow-50', border: 'border-yellow-400', text: 'text-yellow-700', badge: 'bg-yellow-400', icon: '⚡' },
  LOW:      { bg: 'bg-green-50',  border: 'border-green-400',  text: 'text-green-700',  badge: 'bg-green-500',  icon: '✅' },
}

const FEAT_LABELS = {
  cause_closure_rate:         'Event cause closure rate',
  city_inc_1d:                'City-wide incidents (1 day)',
  corridor_closure_rate:      'Corridor closure rate',
  corridor_days_since_last:   'Days since last incident',
  grid_closure_rate:          'Grid cell closure rate',
  llm_subtype_le:             'LLM: Incident subtype',
  corridor_cause_risk:        'Corridor × cause risk',
  latitude:                   'Location (lat)',
  llm_severity_score:         'LLM: Severity score',
  dist_centroid_km:           'Distance from city centre',
  is_planned:                 'Planned event flag',
  is_peak:                    'Peak hour flag',
  event_cause_norm_le:        'Event cause (encoded)',
  hour:                       'Hour of day',
  planned_cause_risk:         'Planned × cause risk',
  peak_cause_risk:            'Peak × cause risk',
  llm_estimated_duration_min: 'LLM: Estimated duration',
  veh_type_le:                'Vehicle type (encoded)',
  corridor_inc_30d:           'Corridor incidents (30d)',
}

function fmtPct(v) { return `${(v * 100).toFixed(0)}%` }
function fmtLabel(key) { return FEAT_LABELS[key] || key.replace(/_/g, ' ') }
function fmtMins(m) {
  if (!m || m < 1) return '<1 min'
  if (m >= 1440) return `~${(m / 1440).toFixed(1)} day(s)`
  if (m >= 60)   return `~${(m / 60).toFixed(1)} h`
  return `~${Math.round(m)} min`
}

// ── Metric card ────────────────────────────────────────────────────────────
function MetricCard({ label, value, sub, accent }) {
  return (
    <div className="card flex flex-col gap-1 min-w-0">
      <span className="label-sm">{label}</span>
      <span className={`text-2xl font-extrabold ${accent || 'text-navy'} leading-none`}>{value}</span>
      {sub && <span className="text-sub text-xs">{sub}</span>}
    </div>
  )
}

// ── Deploy card ────────────────────────────────────────────────────────────
function DeployCard({ icon, label, value, note }) {
  return (
    <div className="card flex items-start gap-3">
      <span className="text-2xl">{icon}</span>
      <div className="min-w-0">
        <p className="label-sm mb-0.5">{label}</p>
        <p className="text-navy font-bold text-base leading-tight">{value}</p>
        {note && <p className="text-sub text-xs mt-0.5 leading-snug">{note}</p>}
      </div>
    </div>
  )
}

// ── SHAP horizontal bar chart ──────────────────────────────────────────────
function ShapChart({ reasons }) {
  const data = reasons.map(r => ({
    name:  fmtLabel(r.feature),
    value: r.contribution,
    abs:   Math.abs(r.contribution),
  })).sort((a, b) => b.abs - a.abs).slice(0, 6)

  const maxAbs = Math.max(...data.map(d => d.abs), 0.01)

  const CustomBar = (props) => {
    const { x, y, width, height, value } = props
    const color = value >= 0 ? '#00C2A8' : '#EF4444'
    return <rect x={x} y={y} width={width} height={height} fill={color} rx={3} />
  }

  return (
    <div>
      <p className="label-sm mb-3">Top closure drivers (SHAP)</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 160 }}>
          <XAxis type="number" domain={[-maxAbs * 1.1, maxAbs * 1.1]} tick={{ fontSize: 11, fill: '#5A6A8A' }} tickLine={false} axisLine={false} tickFormatter={v => v.toFixed(2)} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#0D1B3E' }} tickLine={false} axisLine={false} width={155} />
          <Tooltip
            cursor={{ fill: 'rgba(0,194,168,0.06)' }}
            contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }}
            formatter={(v) => [v.toFixed(4), 'SHAP contribution']}
          />
          <ReferenceLine x={0} stroke="#C8DEFF" strokeWidth={1.5} />
          <Bar dataKey="value" shape={<CustomBar />} />
        </BarChart>
      </ResponsiveContainer>
      <p className="text-sub text-xs mt-2">Positive = raises closure risk · Negative = lowers it</p>
    </div>
  )
}

// ── Empty / hero state ─────────────────────────────────────────────────────
function EmptyState() {
  const stats = [
    { n: '8,171', l: 'Incidents trained on' },
    { n: '47',    l: 'Leakage-safe features' },
    { n: '3.74×', l: 'PR-AUC lift (T1)' },
    { n: '65.8%', l: 'Bucket accuracy (T3)' },
  ]
  return (
    <div className="space-y-6">
      <div className="rounded-2xl overflow-hidden" style={{ background: 'linear-gradient(135deg, #0D1B3E 0%, #1a3460 100%)' }}>
        <div className="px-8 py-10">
          <p className="text-teal text-xs font-bold uppercase tracking-widest mb-3">Flipkart × BTP · PS2</p>
          <h2 className="text-white text-3xl font-extrabold leading-tight mb-3">
            Incident Impact<br />Forecasting
          </h2>
          <p className="text-ice/70 text-sm leading-relaxed max-w-lg">
            Fill in the incident report in the sidebar and click{' '}
            <span className="text-teal font-semibold">FORECAST IMPACT</span> to get
            closure risk, dispatch priority, duration estimate, and a full deployment plan.
          </p>
        </div>
        <div className="grid grid-cols-4 border-t border-white/10">
          {stats.map(s => (
            <div key={s.l} className="px-6 py-4 border-r border-white/10 last:border-r-0">
              <p className="text-teal font-extrabold text-xl">{s.n}</p>
              <p className="text-ice/50 text-xs uppercase tracking-wide mt-0.5">{s.l}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { step: '1', title: 'Fill the form', desc: 'Select corridor, cause, vehicle type, and time in the left panel.' },
          { step: '2', title: 'Add officer notes', desc: 'Paste the incident description — the LLM extracts severity, subtype, and tow need.' },
          { step: '3', title: 'Read the plan', desc: 'Get T1 closure risk, T2 priority, T3 duration bucket, and a full ops deployment plan.' },
        ].map(s => (
          <div key={s.step} className="card flex gap-3">
            <div className="w-7 h-7 rounded-full bg-teal/10 text-teal font-extrabold text-sm flex items-center justify-center flex-shrink-0">
              {s.step}
            </div>
            <div>
              <p className="text-navy font-semibold text-sm mb-0.5">{s.title}</p>
              <p className="text-sub text-xs leading-relaxed">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Loading skeleton ────────────────────────────────────────────────────────
function Skeleton({ className }) {
  return <div className={`bg-navy/10 rounded-lg animate-pulse ${className}`} />
}

function LoadingState() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-20 rounded-xl" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
      </div>
      <div className="grid grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
      </div>
      <Skeleton className="h-56 rounded-xl" />
    </div>
  )
}

// ── Main result view ────────────────────────────────────────────────────────
function ResultView({ data }) {
  const { pred, plan, closure_reasons, llm_extract } = data
  const level = plan.alert_level || 'LOW'
  const style = ALERT_STYLES[level] || ALERT_STYLES.LOW

  const closurePct   = fmtPct(pred.closure_prob)
  const priorityText = pred.priority
  const durationText = pred.duration_bucket
  const severityText = `${pred.severity}/5`

  return (
    <div className="space-y-5">
      {/* Alert banner */}
      <div className={`rounded-xl border-2 p-4 flex items-start gap-4 ${style.bg} ${style.border}`}>
        <span className="text-2xl">{style.icon}</span>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold text-white ${style.badge}`}>
              {level}
            </span>
            <span className={`font-bold text-sm ${style.text}`}>
              {pred.event_cause?.replace(/_/g, ' ')} on {pred.corridor}
            </span>
          </div>
          <p className={`text-sm leading-relaxed ${style.text}`}>
            {plan.summary?.split('\n').slice(1).join(' · ')}
          </p>
        </div>
      </div>

      {/* T1 / T2 / T3 / Severity metric row */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          label="Closure Risk"
          value={closurePct}
          sub={`threshold ${fmtPct(0.256)}`}
          accent={parseFloat(closurePct) >= 40 ? 'text-red-600' : 'text-navy'}
        />
        <MetricCard
          label="Priority"
          value={priorityText}
          sub={`${fmtPct(pred.priority_prob)} confidence`}
          accent={priorityText === 'High' ? 'text-amber-600' : 'text-green-600'}
        />
        <MetricCard
          label="Duration Bucket"
          value={durationText}
          sub={fmtMins(pred.resolution_min) + ' (log1p est.)'}
        />
        <MetricCard
          label="Severity"
          value={severityText}
          sub={pred.incident_subtype?.replace(/_/g, ' ') || '—'}
          accent={pred.severity >= 4 ? 'text-red-600' : pred.severity >= 3 ? 'text-amber-600' : 'text-navy'}
        />
      </div>

      {/* Deployment plan row */}
      <div className="grid grid-cols-2 gap-4">
        <DeployCard
          icon="👮"
          label="Officers to deploy"
          value={`${plan.manpower_officers} officers`}
          note={plan.manpower_rationale?.join(' · ')}
        />
        <DeployCard
          icon="🚧"
          label="Barricades"
          value={plan.barricades > 0 ? `${plan.barricades} barricades` : 'None required'}
          note={plan.barricades > 0 ? 'Road closure likely — set up perimeter' : 'Closure risk is low'}
        />
        <DeployCard
          icon="🔀"
          label="Traffic diversion"
          value={plan.need_diversion ? `Divert → ${plan.diversion_to}` : 'No diversion needed'}
          note={plan.need_diversion ? 'Activate alternate corridor signage' : ''}
        />
        <DeployCard
          icon={plan.tow_required ? '🏗️' : '✅'}
          label="Additional resources"
          value={plan.tow_required ? 'Dispatch tow / crane' : 'Standard equipment'}
          note={`Est. clearance: ${plan.estimated_clearance}`}
        />
      </div>

      {/* SHAP chart */}
      {closure_reasons?.length > 0 && (
        <div className="card">
          <ShapChart reasons={closure_reasons} />
        </div>
      )}

      {/* LLM extraction summary */}
      {llm_extract && (
        <details className="card group" open={false}>
          <summary className="cursor-pointer font-semibold text-navy text-sm select-none flex items-center gap-2">
            <span className="text-teal">▶</span>
            LLM text-mining extraction
          </summary>
          <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t border-black/5">
            {[
              { label: 'Severity score', value: `${llm_extract.severity_score}/5` },
              { label: 'Blocking lanes', value: llm_extract.blocking_lanes ? 'Yes' : 'No' },
              { label: 'Requires tow',   value: llm_extract.requires_tow ? 'Yes' : 'No' },
              { label: 'Vehicles involved', value: String(llm_extract.vehicles_involved) },
              { label: 'Incident subtype',  value: llm_extract.incident_subtype?.replace(/_/g, ' ') || '—' },
              { label: 'Est. duration',     value: fmtMins(pred.resolution_min) },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="label-sm mb-0.5">{label}</p>
                <p className="text-navy font-semibold text-sm">{value}</p>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

// ── Exported component ──────────────────────────────────────────────────────
export default function ForecastTab({ result, loading }) {
  if (loading)  return <LoadingState />
  if (!result)  return <EmptyState />
  return <ResultView data={result} />
}
