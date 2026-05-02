'use client'
import { useState, useEffect, useCallback } from 'react'
import { BarChart3, TrendingUp, Clock, Zap } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  LineChart, Line
} from 'recharts'
import { Incident } from '@/lib/types'
import { fmtDuration } from '@/lib/utils'

export default function AnalyticsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading,   setLoading]   = useState(true)

  const fetchAll = useCallback(async () => {
    try {
      const r = await fetch('/api/incidents')
      const d = await r.json()
      setIncidents(d.incidents || [])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchAll(); const i = setInterval(fetchAll, 10000); return () => clearInterval(i) }, [fetchAll])

  const total    = incidents.length
  const resolved = incidents.filter(i => i.status === 'resolved').length
  const failed   = incidents.filter(i => i.status?.includes('failed')).length
  const open     = incidents.filter(i => ['open','in_progress'].includes(i.status)).length

  const resRate  = total > 0 ? Math.round(resolved/total*100) : 0

  const avgResMs = (() => {
    const times = incidents.filter(i => i.resolved_at)
      .map(i => (new Date(i.resolved_at!).getTime() - new Date(i.created_at).getTime()) / 1000)
    if (!times.length) return 0
    return times.reduce((a,b) => a+b,0) / times.length
  })()

  // Alert type breakdown
  const alertCounts = incidents.reduce((acc, i) => {
    acc[i.alert_name] = (acc[i.alert_name] || 0) + 1
    return acc
  }, {} as Record<string,number>)
  const alertData = Object.entries(alertCounts)
    .sort((a,b) => b[1]-a[1])
    .slice(0,6)
    .map(([name,count]) => ({ name: name.replace(/([A-Z])/g,' $1').trim().slice(0,16), count }))

  // Status pie
  const pieData = [
    { name: 'Resolved', value: resolved, color: '#059669' },
    { name: 'Open',     value: open,     color: '#d97706' },
    { name: 'Failed',   value: failed,   color: '#dc2626' },
  ].filter(d => d.value > 0)

  // Resolution time buckets
  const timeBuckets = incidents.filter(i => i.resolved_at).map(i => ({
    id:  i.id.slice(0,6),
    sec: Math.round((new Date(i.resolved_at!).getTime() - new Date(i.created_at).getTime()) / 1000),
  })).slice(-12)

  const chartStyle = {
    contentStyle: { background: '#0d1729', border: '1px solid #1e3050', borderRadius: 8, fontSize: 11, fontFamily: 'JetBrains Mono' },
    tickStyle:    { fill: '#4a5f84', fontSize: 10, fontFamily: 'JetBrains Mono' },
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">

      <div className="animate-fade-up">
        <h1 className="font-display text-2xl font-700 text-dim-2 tracking-tight">Analytics</h1>
        <p className="text-sm text-slate-3 mt-1">Performance metrics and incident intelligence</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: 'Resolution Rate',   value: `${resRate}%`,  color: '#059669', icon: TrendingUp, sub: `${resolved}/${total} resolved` },
          { label: 'Avg Resolution',    value: avgResMs < 60 ? `${avgResMs.toFixed(0)}s` : `${(avgResMs/60).toFixed(1)}m`, color: '#2563eb', icon: Clock, sub: 'Mean time to resolve' },
          { label: 'Total Incidents',   value: total,           color: '#7c3aed', icon: BarChart3, sub: `${incidents.filter(i=>i.severity==='critical').length} critical` },
          { label: 'Failed Resolutions',value: failed,          color: '#dc2626', icon: Zap, sub: failed > 0 ? 'Need manual review' : 'None ✓' },
        ].map((k, i) => (
          <div key={k.label} className="card p-5 animate-fade-up hover:translate-y-[-2px] transition-transform"
            style={{ animationDelay: `${i*60}ms` }}>
            <div className="flex items-center justify-between mb-3">
              <k.icon size={16} style={{ color: k.color }} />
            </div>
            <div className="font-display text-3xl font-700 tracking-tight mb-1" style={{ color: k.color }}>
              {loading ? '—' : k.value}
            </div>
            <div className="text-sm font-medium text-dim">{k.label}</div>
            <div className="text-xs text-slate-3 mt-1">{k.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Alert type bar chart */}
        <div className="card p-5 animate-fade-up" style={{ animationDelay: '240ms' }}>
          <div className="section-title">📊 Incidents by Alert Type</div>
          {alertData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-sm text-slate-3 opacity-50">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={alertData} margin={{ top: 4, right: 4, bottom: 20, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#152236" />
                <XAxis dataKey="name" tick={{ ...chartStyle.tickStyle, angle: -20, textAnchor: 'end' }} />
                <YAxis tick={chartStyle.tickStyle} allowDecimals={false} />
                <Tooltip contentStyle={chartStyle.contentStyle} />
                <Bar dataKey="count" fill="#2563eb" radius={[4,4,0,0]} name="Incidents" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Status pie */}
        <div className="card p-5 animate-fade-up" style={{ animationDelay: '300ms' }}>
          <div className="section-title">🍩 Status Distribution</div>
          {pieData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-sm text-slate-3 opacity-50">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                  paddingAngle={3} dataKey="value">
                  {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip contentStyle={chartStyle.contentStyle} />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: '#6b7fa0' }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Resolution time chart */}
        <div className="card p-5 animate-fade-up lg:col-span-2" style={{ animationDelay: '360ms' }}>
          <div className="section-title">⏱ Resolution Time per Incident (seconds)</div>
          {timeBuckets.length < 2 ? (
            <div className="h-48 flex items-center justify-center text-sm text-slate-3 opacity-50">
              Need at least 2 resolved incidents
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={timeBuckets} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#152236" />
                <XAxis dataKey="id" tick={chartStyle.tickStyle} />
                <YAxis tick={chartStyle.tickStyle} />
                <Tooltip contentStyle={chartStyle.contentStyle} formatter={(v:any) => [`${v}s`, 'Resolution time']} />
                <Line type="monotone" dataKey="sec" stroke="#7c3aed" strokeWidth={2.5} dot={{ fill: '#7c3aed', r: 4 }} name="Seconds" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Summary table */}
      {incidents.length > 0 && (
        <div className="card overflow-hidden animate-fade-up" style={{ animationDelay: '420ms' }}>
          <div className="px-5 py-4 border-b border-ink-4">
            <div className="section-title" style={{ marginBottom: 0 }}>📋 All Incidents Summary</div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-ink-4">
                  {['ID','Alert','Pod','Severity','Status','Resolution Time','Action'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold tracking-wider uppercase text-slate-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-4">
                {incidents.map(inc => (
                  <tr key={inc.id} className="hover:bg-ink-3/50 transition-colors">
                    <td className="px-4 py-3 text-blue-mid">{inc.id}</td>
                    <td className="px-4 py-3 text-dim max-w-36 truncate">{inc.alert_name}</td>
                    <td className="px-4 py-3 text-slate-3 max-w-36 truncate">{inc.pod_name}</td>
                    <td className="px-4 py-3">
                      <span style={{ color: inc.severity==='critical'?'#dc2626':'#d97706' }}>
                        {inc.severity.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span style={{ color: inc.status==='resolved'?'#059669':inc.status.includes('failed')?'#dc2626':'#d97706' }}>
                        {inc.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-3">{fmtDuration(inc.created_at, inc.resolved_at)}</td>
                    <td className="px-4 py-3 text-slate-3 max-w-48 truncate">{(inc.action_taken||'—').slice(0,40)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
