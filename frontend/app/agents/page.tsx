'use client'
import { useState, useEffect, useCallback } from 'react'
import { Server, Brain, Wrench, Database, Activity, RefreshCw } from 'lucide-react'

const AGENTS = [
  {
    id: 'supervisor', name: 'Supervisor Agent', icon: Server, color: '#2563eb',
    role: 'Alert Dispatcher', description: 'Receives Prometheus AlertManager webhooks, resolves pod names, collects logs, and dispatches incidents to the Evaluator queue.',
    tech: ['Flask 3.1', 'Redis Publisher', 'K8s Client', 'Port 5001'],
    actions: ['Receive webhook', 'Resolve pod name', 'Fetch pod logs', 'Create Incident object', 'Push to queue'],
  },
  {
    id: 'evaluator', name: 'Evaluator Agent', icon: Brain, color: '#7c3aed',
    role: 'AI Analyst', description: 'Consumes incidents from Redis queue, sends logs to Groq Llama 3.3 70B for diagnosis, enriches the incident with structured JSON output.',
    tech: ['Groq SDK', 'Redis Consumer', 'Llama 3.3 70B', 'JSON parser'],
    actions: ['Consume from queue', 'Build LLM prompt', 'Call Groq API', 'Parse JSON response', 'Enrich incident', 'Forward to Resolver'],
  },
  {
    id: 'resolver', name: 'Resolver Agent', icon: Wrench, color: '#059669',
    role: 'Remediation Engine', description: 'Executes real Kubernetes API actions based on AI diagnosis. Supports 9 action types plus smart fallback for unknown incidents.',
    tech: ['K8s Client v35', 'Redis Consumer', 'NetworkPolicy API', 'RBAC'],
    actions: ['Restart pod', 'Patch resource limits', 'Scale deployment', 'Reset NetworkPolicy', 'Rollback deployment', 'Cordon node', 'Smart fallback'],
  },
]

export default function AgentsPage() {
  const [health,   setHealth]   = useState<any>(null)
  const [loading,  setLoading]  = useState(true)
  const [incidents, setIncidents] = useState<any[]>([])

  const fetchAll = useCallback(async () => {
    try {
      const [hr, ir] = await Promise.all([fetch('/api/health'), fetch('/api/incidents')])
      setHealth(await hr.json())
      const id = await ir.json()
      setIncidents(id.incidents || [])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchAll(); const i = setInterval(fetchAll, 8000); return () => clearInterval(i) }, [fetchAll])

  const online = health?.status === 'healthy'

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">

      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="font-display text-2xl font-700 text-dim-2 tracking-tight">Agent Status</h1>
          <p className="text-sm text-slate-3 mt-1">Real-time status of all autonomous pipeline agents</p>
        </div>
        <button onClick={fetchAll} className="btn-ghost">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* System health bar */}
      <div className={`card p-4 border animate-fade-up flex items-center gap-4
        ${online ? 'border-green/30 bg-green/5' : 'border-red/30 bg-red/5'}`}
        style={{ animationDelay: '60ms' }}>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center
          ${online ? 'bg-green/15' : 'bg-red/15'}`}>
          <Activity size={18} className={online ? 'text-green' : 'text-red'} />
        </div>
        <div>
          <div className={`font-semibold text-sm ${online ? 'text-green' : 'text-red'}`}>
            {online ? 'All Systems Operational' : 'System Offline'}
          </div>
          <div className="text-xs text-slate-3 font-mono mt-0.5">
            Redis: {health?.redis || '—'} · Last checked: {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : '—'}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-6 text-center">
          {[
            { label: 'Total', value: incidents.length, color: 'text-blue' },
            { label: 'Resolved', value: incidents.filter(i=>i.status==='resolved').length, color: 'text-green' },
            { label: 'Open', value: incidents.filter(i=>['open','in_progress'].includes(i.status)).length, color: 'text-amber' },
          ].map(m => (
            <div key={m.label}>
              <div className={`font-display text-xl font-700 ${m.color}`}>{m.value}</div>
              <div className="text-[10px] text-slate-3 font-mono">{m.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Agent cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {AGENTS.map((agent, i) => (
          <div key={agent.id} className="card p-5 animate-fade-up hover:translate-y-[-2px] transition-transform duration-200"
            style={{ animationDelay: `${120 + i*60}ms`, borderColor: online ? `${agent.color}25` : undefined }}>

            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center border"
                style={{ background: `${agent.color}12`, borderColor: `${agent.color}30` }}>
                <agent.icon size={20} style={{ color: agent.color }} />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-sm text-dim-2">{agent.name}</div>
                <div className="text-xs text-slate-3">{agent.role}</div>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full animate-pulse-dot"
                  style={{ background: online ? agent.color : '#4a5f84' }} />
                <span className="text-[10px] font-mono font-semibold"
                  style={{ color: online ? agent.color : '#4a5f84' }}>
                  {online ? 'ONLINE' : 'OFFLINE'}
                </span>
              </div>
            </div>

            {/* Description */}
            <p className="text-xs text-slate-3 leading-relaxed mb-4">{agent.description}</p>

            {/* Tech stack */}
            <div className="mb-4">
              <div className="text-[9px] font-semibold tracking-widest uppercase text-slate-font-mono mb-2" style={{color:'#6b7fa0'}}>
                Tech Stack
              </div>
              <div className="flex flex-wrap gap-1.5">
                {agent.tech.map(t => (
                  <span key={t} className="text-[10px] font-mono px-2 py-0.5 rounded border border-ink-4 text-slate-3 bg-ink-3">
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div>
              <div className="text-[9px] font-semibold tracking-widest uppercase mb-2" style={{color:'#6b7fa0'}}>
                Capabilities
              </div>
              <div className="space-y-1">
                {agent.actions.map(a => (
                  <div key={a} className="flex items-center gap-2 text-xs text-slate-3">
                    <div className="w-1 h-1 rounded-full flex-shrink-0" style={{ background: agent.color }} />
                    {a}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Redis + pipeline */}
      <div className="card p-5 animate-fade-up" style={{ animationDelay: '360ms' }}>
        <div className="section-title">🗄 Message Queue — Redis</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { label: 'Supervisor → Evaluator', key: 'queue:supervisor:evaluator', color: '#2563eb' },
            { label: 'Evaluator → Resolver',   key: 'queue:evaluator:resolver',   color: '#7c3aed' },
            { label: 'Incident Store',          key: 'store:incidents',            color: '#059669' },
          ].map(q => (
            <div key={q.key} className="bg-ink-3 border border-ink-4 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Database size={14} style={{ color: q.color }} />
                <span className="text-xs font-semibold" style={{ color: q.color }}>{q.label}</span>
              </div>
              <div className="font-mono text-[10px] text-slate-3">{q.key}</div>
              <div className="mt-2 text-xs text-slate-3">
                {q.key === 'store:incidents'
                  ? `${incidents.length} records`
                  : 'LPUSH / BRPOP transport'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
