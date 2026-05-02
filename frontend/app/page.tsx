'use client'
import { useState, useEffect, useCallback } from 'react'
import { Activity, CheckCircle2, AlertTriangle, XCircle, Clock, Zap, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import StatCard    from '@/components/ui/StatCard'
import Skeleton    from '@/components/ui/Skeleton'
import SeverityBadge from '@/components/ui/SeverityBadge'
import StatusBadge   from '@/components/ui/StatusBadge'
import { Incident } from '@/lib/types'
import { fmtTime, fmtDuration, SEV_CONFIG } from '@/lib/utils'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts'

const ALERTS = [
  { label: '🔴 High Memory',    value: 'HighMemoryUsage|critical'            },
  { label: '🟡 High CPU',       value: 'HighCPUUsage|warning'                },
  { label: '🔴 Crash Loop',     value: 'PodCrashLooping|critical'            },
  { label: '🔴 Network Fail',   value: 'NetworkConnectivityFailure|critical' },
  { label: '🔴 Deploy Down',    value: 'DeploymentUnavailable|critical'      },
  { label: '🟡 Pod Not Ready',  value: 'PodNotReady|warning'                 },
]

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [chart,     setChart]     = useState<any[]>([])
  const [loading,   setLoading]   = useState(true)
  const [alertSel,  setAlertSel]  = useState(ALERTS[0].value)
  const [firing,    setFiring]    = useState(false)
  const [fireMsg,   setFireMsg]   = useState('')

  const fetchAll = useCallback(async () => {
    try {
      const r  = await fetch('/api/incidents')
      const d  = await r.json()
      const list: Incident[] = d.incidents || []
      setIncidents(list)
      const total    = list.length
      const resolved = list.filter(i => i.status === 'resolved').length
      const open     = list.filter(i => ['open','in_progress'].includes(i.status)).length
      const failed   = list.filter(i => i.status?.includes('failed')).length
      setChart(p => [...p, {
        time: new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'}),
        total, resolved, open, failed
      }].slice(-16))
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchAll(); const id = setInterval(fetchAll, 8000); return () => clearInterval(id) }, [fetchAll])

  const fireAlert = async () => {
    setFiring(true); setFireMsg('')
    const [alertname, severity] = alertSel.split('|')
    try {
      const r = await fetch('/api/trigger', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alertname, namespace: 'default', pod: 'demo-app', severity })
      })
      const d = await r.json()
      setFireMsg(d.processed ? `✓ ${d.processed} incident dispatched` : '⚠ No response')
      setTimeout(fetchAll, 3000); setTimeout(fetchAll, 8000)
    } catch { setFireMsg('✗ Supervisor offline') }
    finally { setFiring(false); setTimeout(() => setFireMsg(''), 6000) }
  }

  const total    = incidents.length
  const resolved = incidents.filter(i => i.status === 'resolved').length
  const open     = incidents.filter(i => ['open','in_progress'].includes(i.status)).length
  const failed   = incidents.filter(i => i.status?.includes('failed')).length
  const avgRes   = (() => {
    const times = incidents.filter(i => i.resolved_at)
      .map(i => (new Date(i.resolved_at!).getTime() - new Date(i.created_at).getTime()) / 1000)
    if (!times.length) return '—'
    const avg = times.reduce((a,b) => a+b,0) / times.length
    return avg < 60 ? `${avg.toFixed(0)}s` : `${(avg/60).toFixed(1)}m`
  })()

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">

      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="font-display text-2xl font-700 text-dim-2 tracking-tight">Operations Dashboard</h1>
        <p className="text-sm text-slate-3 mt-1">Real-time visibility into your autonomous AI agent pipeline</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Total Incidents"    value={loading ? '—' : total}    icon={Activity}     color="#2563eb" delay={0}   sub={`${incidents.filter(i=>i.severity==='critical').length} critical`} />
        <StatCard label="Resolved"           value={loading ? '—' : resolved} icon={CheckCircle2} color="#059669" delay={60}  sub={total > 0 ? `${Math.round(resolved/total*100)}% rate` : 'No data'} />
        <StatCard label="Open / Active"      value={loading ? '—' : open}     icon={AlertTriangle} color="#d97706" delay={120} sub={open > 0 ? 'Awaiting resolution' : 'All clear ✓'} />
        <StatCard label="Avg Resolution"     value={loading ? '—' : avgRes}   icon={Clock}        color="#7c3aed" delay={180} sub="Mean time to resolve" />
      </div>

      {/* Middle row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Agent pipeline */}
        <div className="card p-5 animate-fade-up" style={{ animationDelay: '200ms' }}>
          <div className="section-title">🔗 Agent Pipeline</div>
          <div className="space-y-3">
            {[
              { icon:'📡', label:'Prometheus',  sub:'Alert source',    color:'#0891b2' },
              { icon:'🖥️', label:'Supervisor',  sub:'Log collector',   color:'#2563eb' },
              { icon:'🧠', label:'Evaluator',   sub:'Groq LLM · AI',  color:'#7c3aed' },
              { icon:'🔧', label:'Resolver',    sub:'K8s remediation', color:'#059669' },
            ].map((n, i) => (
              <div key={n.label}>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center text-sm flex-shrink-0"
                    style={{ background: `${n.color}15`, border: `1px solid ${n.color}30` }}>
                    {n.icon}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-dim">{n.label}</div>
                    <div className="text-xs text-slate-3">{n.sub}</div>
                  </div>
                  <div className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: n.color }} />
                </div>
                {i < 3 && (
                  <div className="ml-4 my-1">
                    <div className="w-px h-3 ml-[14px]" style={{ background: `${n.color}40` }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Live chart */}
        <div className="lg:col-span-2 card p-5 animate-fade-up" style={{ animationDelay: '250ms' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="section-title" style={{ marginBottom: 0 }}>📈 Incident Rate — Live</div>
            <div className="flex gap-3 text-xs">
              {[['Total','#2563eb'],['Resolved','#059669'],['Open','#d97706']].map(([l,c]) => (
                <span key={l} className="flex items-center gap-1.5 text-slate-3">
                  <span className="w-2.5 h-0.5 rounded" style={{ background: c }} />{l}
                </span>
              ))}
            </div>
          </div>
          {chart.length < 2 ? (
            <div className="h-48 flex flex-col items-center justify-center gap-2 opacity-40">
              <Activity size={28} className="text-slate-3" />
              <div className="text-xs text-slate-3">Fire an alert to populate the chart</div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={192}>
              <AreaChart data={chart} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  {[['t','#2563eb'],['r','#059669'],['o','#d97706']].map(([id,c]) => (
                    <linearGradient key={id} id={`g${id}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={c} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={c} stopOpacity={0}   />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#152236" />
                <XAxis dataKey="time" tick={{ fill: '#4a5f84', fontSize: 10, fontFamily: 'JetBrains Mono' }} />
                <YAxis tick={{ fill: '#4a5f84', fontSize: 10, fontFamily: 'JetBrains Mono' }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#0d1729', border: '1px solid #1e3050', borderRadius: 8, fontSize: 11, fontFamily: 'JetBrains Mono' }} />
                <Area type="monotone" dataKey="total"    stroke="#2563eb" fill="url(#gt)" strokeWidth={2} dot={false} name="Total" />
                <Area type="monotone" dataKey="resolved" stroke="#059669" fill="url(#gr)" strokeWidth={2} dot={false} name="Resolved" />
                <Area type="monotone" dataKey="open"     stroke="#d97706" fill="url(#go)" strokeWidth={2} dot={false} name="Open" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Fire alert + recent incidents */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Fire alert */}
        <div className="card p-5 border-blue/20 bg-blue/5 animate-fade-up" style={{ animationDelay: '300ms' }}>
          <div className="section-title">⚡ Simulate Alert</div>
          <div className="space-y-3">
            <select value={alertSel} onChange={e => setAlertSel(e.target.value)} className="input">
              {ALERTS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
            </select>
            <button onClick={fireAlert} disabled={firing} className="btn-primary w-full justify-center">
              {firing ? <><RefreshCw size={14} className="animate-spin" />Dispatching…</> : <><Zap size={14} />Fire Alert</>}
            </button>
            {fireMsg && (
              <div className={`text-xs font-mono px-3 py-2 rounded-lg
                ${fireMsg.startsWith('✓') ? 'bg-green/10 text-green border border-green/20'
                  : 'bg-red/10 text-red border border-red/20'}`}>
                {fireMsg}
              </div>
            )}
          </div>
        </div>

        {/* Recent incidents */}
        <div className="lg:col-span-2 card p-5 animate-fade-up" style={{ animationDelay: '350ms' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="section-title" style={{ marginBottom: 0 }}>🕐 Recent Incidents</div>
            <Link href="/incidents" className="text-xs text-blue hover:text-blue-mid transition-colors">
              View all →
            </Link>
          </div>
          {loading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : incidents.length === 0 ? (
            <div className="text-center py-8 text-sm text-slate-3 opacity-50">
              No incidents yet — fire a test alert
            </div>
          ) : (
            <div className="space-y-2">
              {incidents.slice(0, 5).map(inc => (
                <Link key={inc.id} href={`/incidents/${inc.id}`}
                  className="flex items-center gap-3 p-3 rounded-lg bg-ink-3 border border-ink-4
                             hover:border-blue/30 hover:bg-blue/5 transition-all duration-150">
                  <div className="w-2 h-2 rounded-full flex-shrink-0 animate-pulse-dot"
                    style={{ background: SEV_CONFIG[inc.severity as keyof typeof SEV_CONFIG]?.dot || '#2563eb' }} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-dim truncate">{inc.alert_name}</div>
                    <div className="text-xs font-mono text-slate-3">{inc.namespace}/{inc.pod_name}</div>
                  </div>
                  <StatusBadge status={inc.status} />
                  <div className="text-xs font-mono text-slate-3 flex-shrink-0">{fmtTime(inc.created_at)}</div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
