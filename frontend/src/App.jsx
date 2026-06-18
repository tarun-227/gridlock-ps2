import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ForecastTab from './components/ForecastTab'
import InsightsTab from './components/InsightsTab'

export default function App() {
  const [activeTab, setActiveTab] = useState('forecast')
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)

  async function handleForecast(formData) {
    setLoading(true)
    setError(null)
    setActiveTab('forecast')
    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Server error' }))
        throw new Error(err.detail || 'Prediction failed')
      }
      const data = await res.json()
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'forecast', label: '⚡ Forecast & Deploy' },
    { id: 'insights', label: '📊 Insights' },
  ]

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────────── */}
      <Sidebar onSubmit={handleForecast} loading={loading} />

      {/* ── Main ────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tab bar */}
        <nav className="bg-navy flex-shrink-0 flex items-center px-2 border-b border-white/10">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-5 py-4 text-sm font-semibold transition-all duration-150 ${
                activeTab === t.id
                  ? 'text-navy bg-teal rounded-t-md -mb-px'
                  : 'text-ice/70 hover:text-white'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <main className="flex-1 overflow-y-auto bg-light-bg">
          <div className="max-w-5xl mx-auto px-6 py-6">
            {error && (
              <div className="mb-5 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm font-medium">
                ⚠️ {error}
              </div>
            )}
            {activeTab === 'forecast'
              ? <ForecastTab result={result} loading={loading} />
              : <InsightsTab />}
          </div>
        </main>
      </div>
    </div>
  )
}
