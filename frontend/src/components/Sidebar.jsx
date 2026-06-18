import { useState } from 'react'

const CORRIDORS = [
  'Non-corridor','Bannerghata Road','Bellary Road 1','Bellary Road 2',
  'Hosur Road','IRR(Thanisandra road)','Magadi Road','Mysore Road',
  'ORR East 1','ORR East 2','ORR North 1','ORR North 2','ORR West 1',
  'Old Madras Road','Tumkur Road','Varthur Road','West of Chord Road',
]

const CAUSES = [
  'vehicle_breakdown','accident','congestion','construction','tree_fall',
  'pot_holes','public_event','procession','vip_movement','protest',
  'water_logging','road_conditions','debris','others',
]

const VEH_TYPES = [
  'two_wheeler','three_wheeler','car','lcv','heavy_vehicle',
  'bus','truck','tanker','container','others',
]

const ZONES = [
  'Central Zone 1','Central Zone 2','East Zone 1','East Zone 2',
  'North Zone 1','North Zone 2','South Zone 1','South Zone 2',
  'West Zone 1','West Zone 2',
]

function now() {
  const d = new Date()
  d.setSeconds(0, 0)
  return d.toISOString().slice(0, 16)
}

function SelectField({ id, value, onChange, options, placeholder }) {
  return (
    <select
      id={id}
      value={value}
      onChange={e => onChange(e.target.value)}
      className="select-field"
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map(o => (
        <option key={o} value={o} className="bg-navy text-white">
          {o.replace(/_/g, ' ')}
        </option>
      ))}
    </select>
  )
}

export default function Sidebar({ onSubmit, loading }) {
  const [form, setForm] = useState({
    corridor:    'Non-corridor',
    event_cause: 'vehicle_breakdown',
    veh_type:    '',
    zone:        '',
    datetime_str: now(),
    is_planned:  false,
    description: '',
    live_llm:    false,
  })

  function set(field) { return v => setForm(f => ({ ...f, [field]: v })) }

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit({
      ...form,
      veh_type: form.veh_type || null,
      zone:     form.zone || null,
    })
  }

  return (
    <aside
      className="w-80 flex-shrink-0 bg-navy flex flex-col h-screen overflow-y-auto"
      style={{ borderRight: '3px solid #00C2A8' }}
    >
      {/* ── Brand ── */}
      <div className="px-6 pt-6 pb-4 border-b border-white/10">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl">🚦</span>
          <h1 className="text-xl font-extrabold text-white tracking-tight">GridLock</h1>
        </div>
        <p className="text-ice/60 text-xs">BTP Congestion Intelligence · PS2</p>
      </div>

      {/* ── Form ── */}
      <form onSubmit={handleSubmit} className="flex-1 px-5 py-5 flex flex-col gap-4">

        <div>
          <label className="block text-ice/70 text-xs font-semibold mb-1.5 uppercase tracking-widest">
            Corridor
          </label>
          <SelectField id="corridor" value={form.corridor} onChange={set('corridor')} options={CORRIDORS} />
        </div>

        <div>
          <label className="block text-ice/70 text-xs font-semibold mb-1.5 uppercase tracking-widest">
            Event Cause
          </label>
          <SelectField id="cause" value={form.event_cause} onChange={set('event_cause')} options={CAUSES} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-ice/70 text-xs font-semibold mb-1.5 uppercase tracking-widest">
              Vehicle
            </label>
            <SelectField id="veh" value={form.veh_type} onChange={set('veh_type')} options={VEH_TYPES} placeholder="Any" />
          </div>
          <div>
            <label className="block text-ice/70 text-xs font-semibold mb-1.5 uppercase tracking-widest">
              Zone
            </label>
            <SelectField id="zone" value={form.zone} onChange={set('zone')} options={ZONES} placeholder="Any" />
          </div>
        </div>

        <div>
          <label className="block text-ice/70 text-xs font-semibold mb-1.5 uppercase tracking-widest">
            Date & Time
          </label>
          <input
            type="datetime-local"
            value={form.datetime_str}
            onChange={e => set('datetime_str')(e.target.value)}
            className="input-field"
          />
        </div>

        <div>
          <label className="block text-ice/70 text-xs font-semibold mb-1.5 uppercase tracking-widest">
            Officer Notes
          </label>
          <textarea
            rows={3}
            value={form.description}
            onChange={e => set('description')(e.target.value)}
            placeholder="huge tree fallen blocking the road, crane needed…"
            className="input-field resize-none leading-relaxed"
          />
        </div>

        <div className="flex flex-col gap-2.5 pt-1">
          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={form.is_planned}
              onChange={e => set('is_planned')(e.target.checked)}
              className="w-4 h-4 accent-teal rounded"
            />
            <div>
              <span className="text-white text-sm font-medium">Planned event</span>
              <p className="text-ice/50 text-xs">Rally, procession, VIP movement</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={form.live_llm}
              onChange={e => set('live_llm')(e.target.checked)}
              className="w-4 h-4 accent-teal rounded"
            />
            <div>
              <span className="text-white text-sm font-medium">Live Groq LLM</span>
              <p className="text-ice/50 text-xs">Re-extract notes in real time</p>
            </div>
          </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className={`mt-auto w-full py-3 rounded-xl font-bold text-navy text-sm tracking-wide transition-all duration-150
            ${loading
              ? 'bg-teal/50 cursor-not-allowed'
              : 'bg-teal hover:brightness-110 active:scale-95 shadow-lg shadow-teal/20'}`}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-navy/40 border-t-navy rounded-full animate-spin" />
              Forecasting…
            </span>
          ) : '⚡ FORECAST IMPACT'}
        </button>
      </form>

      {/* ── Footer stats ── */}
      <div className="px-5 py-4 border-t border-white/10 text-ice/40 text-xs space-y-1">
        <p>Models trained on 8,171 incidents</p>
        <p>Nov 2023 – Apr 2024 · BTP dataset</p>
        <p className="text-teal/70 font-semibold mt-1">T1 · T2 · T3 · Recommendation</p>
      </div>
    </aside>
  )
}
