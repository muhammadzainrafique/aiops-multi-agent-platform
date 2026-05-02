'use client'
import { useState, useEffect, useCallback } from 'react'
import { Search, Filter, RefreshCw, AlertTriangle } from 'lucide-react'
import Link from 'next/link'
import SeverityBadge from '@/components/ui/SeverityBadge'
import StatusBadge   from '@/components/ui/StatusBadge'
import Skeleton      from '@/components/ui/Skeleton'
import EmptyState    from '@/components/ui/EmptyState'
import { Incident }  from '@/lib/types'
import { fmtTime, fmtDuration, SEV_CONFIG } from '@/lib/utils'

const FILTERS = ['all','open','resolved','evaluation_failed','resolution_failed'] as const

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading,   setLoading]   = useState(true)
  const [filter,    setFilter]    = useState<string>('all')
  const [search,    setSearch]    = useState('')
  const [sevFilter, setSevFilter] = useState('all')

  const fetchAll = useCallback(async () => {
    try {
      const r = await fetch('/api/incidents')
      const d = await r.json()
      setIncidents(d.incidents || [])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchAll(); const id = setInterval(fetchAll, 8000); return () => clearInterval(id) }, [fetchAll])

  const filtered = incidents.filter(inc => {
    const matchFilter = filter === 'all' || inc.status === filter ||
      (filter === 'open' && ['open','in_progress'].includes(inc.status))
    const matchSev    = sevFilter === 'all' || inc.severity === sevFilter
    const matchSearch = !search || inc.alert_name.toLowerCase().includes(search.toLowerCase()) ||
      inc.pod_name.toLowerCase().includes(search.toLowerCase()) ||
      inc.id.toLowerCase().includes(search.toLowerCase())
    return matchFilter && matchSev && matchSearch
  })

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="font-display text-2xl font-700 text-dim-2 tracking-tight">Incidents</h1>
          <p className="text-sm text-slate-3 mt-1">{incidents.length} total · {incidents.filter(i=>i.status==='resolved').length} resolved</p>
        </div>
        <button onClick={fetchAll} className="btn-ghost">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 animate-fade-up" style={{ animationDelay: '60ms' }}>
        {/* Search */}
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-3" />
          <input className="input pl-9" placeholder="Search by alert, pod, or ID…"
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>

        {/* Status filter */}
        <div className="flex gap-1.5 bg-ink-2 border border-ink-4 rounded-lg p-1">
          {[
            { key: 'all',      label: 'All' },
            { key: 'open',     label: 'Open' },
            { key: 'resolved', label: 'Resolved' },
            { key: 'evaluation_failed', label: 'Failed' },
          ].map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-150
                ${filter === f.key
                  ? 'bg-blue text-white shadow-sm'
                  : 'text-slate-3 hover:text-dim hover:bg-ink-3'}`}>
              {f.label}
            </button>
          ))}
        </div>

        {/* Severity filter */}
        <div className="flex gap-1.5 bg-ink-2 border border-ink-4 rounded-lg p-1">
          {['all','critical','warning'].map(s => (
            <button key={s} onClick={() => setSevFilter(s)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition-all duration-150
                ${sevFilter === s
                  ? 'bg-blue text-white shadow-sm'
                  : 'text-slate-3 hover:text-dim hover:bg-ink-3'}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden animate-fade-up" style={{ animationDelay: '120ms' }}>
        {/* Table header */}
        <div className="grid grid-cols-12 gap-3 px-5 py-3 border-b border-ink-4 text-xs font-semibold tracking-wider uppercase text-slate-3">
          <div className="col-span-3">Alert</div>
          <div className="col-span-3">Pod</div>
          <div className="col-span-1">Severity</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-2">Time / Duration</div>
          <div className="col-span-1 text-right">Action</div>
        </div>

        {loading ? (
          <div className="p-4 space-y-3">
            {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-14 w-full" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={AlertTriangle} title="No incidents found"
            sub={search ? 'Try a different search term' : 'Fire a test alert from the dashboard'} />
        ) : (
          <div className="divide-y divide-ink-4">
            {filtered.map((inc, idx) => {
              const sevCfg = SEV_CONFIG[inc.severity as keyof typeof SEV_CONFIG] || SEV_CONFIG.info
              return (
                <div key={inc.id}
                  className="grid grid-cols-12 gap-3 px-5 py-4 items-center
                             hover:bg-ink-3/50 transition-colors duration-100
                             animate-fade-up"
                  style={{ animationDelay: `${idx * 30}ms` }}>
                  <div className="col-span-3 flex items-center gap-2.5">
                    <div className="w-2 h-2 rounded-full flex-shrink-0 animate-pulse-dot"
                      style={{ background: sevCfg.dot }} />
                    <div>
                      <div className="text-sm font-semibold text-dim">{inc.alert_name}</div>
                      <div className="text-xs font-mono text-slate-3 mt-0.5">{inc.id}</div>
                    </div>
                  </div>
                  <div className="col-span-3">
                    <div className="text-sm font-mono text-dim">{inc.pod_name}</div>
                    <div className="text-xs text-slate-3 mt-0.5">{inc.namespace}</div>
                  </div>
                  <div className="col-span-1">
                    <SeverityBadge severity={inc.severity} size="sm" />
                  </div>
                  <div className="col-span-2">
                    <StatusBadge status={inc.status} />
                  </div>
                  <div className="col-span-2">
                    <div className="text-xs font-mono text-dim">{fmtTime(inc.created_at)}</div>
                    <div className="text-xs text-slate-3 mt-0.5">
                      {fmtDuration(inc.created_at, inc.resolved_at)}
                    </div>
                  </div>
                  <div className="col-span-1 flex justify-end">
                    <Link href={`/incidents/${inc.id}`}
                      className="text-xs text-blue hover:text-blue-mid font-semibold
                                 px-3 py-1.5 rounded-lg border border-blue/20 hover:border-blue/40
                                 bg-blue/5 hover:bg-blue/10 transition-all duration-150">
                      View →
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
