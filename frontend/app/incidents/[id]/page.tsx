'use client'
import { useState, useEffect, useRef, use } from 'react'
import { ArrowLeft, Brain, Server, Wrench, Bell, Send, Loader2, FileCode } from 'lucide-react'
import Link from 'next/link'
import SeverityBadge from '@/components/ui/SeverityBadge'
import StatusBadge from '@/components/ui/StatusBadge'
import { Incident } from '@/lib/types'
import { fmtTime, fmtDate, fmtDuration, colorizeLog, buildDiff } from '@/lib/utils'
import Skeleton from '@/components/ui/Skeleton'
// ── Sub-components ────────────────────────────────────────────────────────────

function TimelineStep({ icon, label, color, tag, tagColor, time, children }: any) {
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center text-base flex-shrink-0 border"
          style={{ background: `${color}12`, borderColor: `${color}30` }}>
          {icon}
        </div>
        <div className="w-px flex-1 mt-2" style={{ background: `${color}20` }} />
      </div>
      <div className="flex-1 pb-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-bold tracking-wider uppercase" style={{ color }}>{label}</span>
          {time && <span className="text-xs font-mono text-slate-3">{time}</span>}
          <span className="text-[9px] font-bold px-2 py-0.5 rounded font-mono"
            style={{ background: `${tagColor}15`, color: tagColor }}>{tag}</span>
        </div>
        {children}
      </div>
    </div>
  )
}

function DiffView({ diff }: { diff: ReturnType<typeof buildDiff> }) {
  if (!diff.length) return null
  return (
    <div className="rounded-lg overflow-hidden border border-ink-4 font-mono text-xs">
      {diff.map((row, i) => {
        if (row.type === 'header') return (
          <div key={i} className="bg-ink-3 px-4 py-2 text-slate-3 flex items-center gap-2">
            <FileCode size={11} /> {row.text}
          </div>
        )
        const styles = {
          del: 'bg-red/8 text-red border-l-2 border-red/60',
          add: 'bg-green/8 text-green border-l-2 border-green/60',
          ctx: 'text-slate-3',
        }[row.type] || 'text-slate-3'
        const sign = row.type === 'del' ? '−' : row.type === 'add' ? '+' : ' '
        return (
          <div key={i} className={`flex px-4 py-1 ${styles}`}>
            <span className="w-4 flex-shrink-0 select-none">{sign}</span>
            <span>{row.text}</span>
          </div>
        )
      })}
    </div>
  )
}

function LogTerminal({ logs }: { logs: string }) {
  const lines = (logs || 'No logs captured').split('\n').filter(l => l.trim())
  return (
    <div className="rounded-lg overflow-hidden border border-ink-4">
      <div className="bg-ink-3 px-4 py-2 flex items-center gap-2 border-b border-ink-4">
        {['#ff5f57', '#febc2e', '#28c840'].map(c => (
          <div key={c} className="w-2.5 h-2.5 rounded-full" style={{ background: c }} />
        ))}
        <span className="ml-2 text-xs font-mono text-slate-3">kubectl logs</span>
        <span className="ml-auto text-xs font-mono text-slate-3">{lines.length} lines</span>
      </div>
      <div className="bg-[#0a0f1a] p-4 max-h-56 overflow-y-auto">
        {lines.map((line, i) => (
          <div key={i} className={`font-mono text-[11px] leading-6 ${colorizeLog(line)}`}>
            {line}
          </div>
        ))}
      </div>
    </div>
  )
}

function ChatPanel({ incident }: { incident: Incident }) {
  const [msgs, setMsgs] = useState<{ role: string; text: string; time: string }[]>([
    {
      role: 'ai', time: 'Ready',
      text: `Hello! I'm your AI Incident Analyst. I have full context on incident <strong>${incident.id}</strong> — <strong>${incident.alert_name}</strong>. Ask me anything about what happened, why, and how it was resolved.`
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<{ role: string; content: string }[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const QUICK = [
    'Explain what happened in plain English',
    'Why did the resolver take this action?',
    'What was the risk if this was not fixed?',
    'How can I prevent this in future?',
    'Summarise in 3 bullet points',
    'What do the logs show?',
  ]

  const send = async (text?: string) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')
    const now = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    setMsgs(p => [...p, { role: 'user', text: msg, time: now }])
    setLoading(true)

    const context = `
Incident ID: ${incident.id}
Alert: ${incident.alert_name}
Pod: ${incident.namespace}/${incident.pod_name}
Severity: ${incident.severity}
Status: ${incident.status}
AI Diagnosis: ${incident.ai_diagnosis || 'Not evaluated'}
Recommended Action: ${incident.recommended_action || '—'}
Action Taken: ${incident.action_taken || '—'}
Raw Logs: ${(incident.raw_logs || '').slice(0, 600)}
Created: ${incident.created_at}
Resolved: ${incident.resolved_at || 'Not yet'}
`
    try {
      const r = await fetch('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, context, history }),
      })
      const d = await r.json()
      const reply = d.reply || 'No response generated.'
      setMsgs(p => [...p, { role: 'ai', text: reply, time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) }])
      setHistory(p => [...p, { role: 'user', content: msg }, { role: 'assistant', content: reply.replace(/<[^>]*>/g, '') }].slice(-12))
    } catch {
      setMsgs(p => [...p, { role: 'ai', text: '⚠️ Chat unavailable. Check your Groq API key in .env.local', time: '—' }])
    } finally { setLoading(false) }
  }

  return (
    <div className="card flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-ink-4 flex items-center gap-3 flex-shrink-0
                      bg-gradient-to-r from-purple/10 to-blue/10">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple to-blue
                        flex items-center justify-center text-base shadow-glow">
          🧠
        </div>
        <div>
          <div className="font-semibold text-sm text-dim-2">AI Incident Analyst</div>
          <div className="text-xs text-slate-3">Powered by Groq Llama 3.3</div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {msgs.map((m, i) => (
          <div key={i} className={`flex gap-2.5 animate-fade-up ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
            style={{ animationDelay: `${i * 30}ms` }}>
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0
              ${m.role === 'ai'
                ? 'bg-gradient-to-br from-purple to-blue'
                : 'bg-ink-4 text-xs font-bold text-dim font-mono'}`}>
              {m.role === 'ai' ? '🧠' : 'ME'}
            </div>
            <div className={`max-w-[82%] ${m.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
              <div className={`px-4 py-3 rounded-xl text-sm leading-relaxed
                ${m.role === 'ai'
                  ? 'bg-ink-3 border border-ink-4 text-dim rounded-tl-sm'
                  : 'bg-blue text-white rounded-tr-sm'}`}
                dangerouslySetInnerHTML={{ __html: m.text }} />
              <div className="text-[10px] font-mono text-slate-3 px-1">{m.time}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple to-blue flex items-center justify-center">🧠</div>
            <div className="bg-ink-3 border border-ink-4 rounded-xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
              {[0, 1, 2].map(i => (
                <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-3 animate-bounce-msg"
                  style={{ animationDelay: `${i * 0.2}s` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      <div className="px-4 py-2 border-t border-ink-4 flex flex-wrap gap-1.5 flex-shrink-0">
        {QUICK.map(q => (
          <button key={q} onClick={() => send(q)} disabled={loading}
            className="text-[10px] px-2.5 py-1 rounded-full border border-ink-4 text-slate-3
                       hover:border-blue/40 hover:text-blue hover:bg-blue/5 transition-all
                       disabled:opacity-50 disabled:cursor-not-allowed">
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-ink-4 flex-shrink-0">
        <div className="flex gap-2 items-end bg-ink-3 border border-ink-4 rounded-xl px-3 py-2
                        focus-within:border-blue/40 focus-within:ring-2 focus-within:ring-blue/8 transition-all">
          <textarea
            className="flex-1 bg-transparent outline-none text-sm text-dim resize-none
                       placeholder:text-slate-3 font-sans leading-snug max-h-20"
            placeholder="Ask about this incident…" rows={1}
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          />
          <button onClick={() => send()} disabled={loading || !input.trim()}
            className="w-7 h-7 rounded-lg bg-blue flex items-center justify-center
                       hover:bg-blue-glow transition-colors disabled:opacity-40 flex-shrink-0">
            {loading ? <Loader2 size={13} className="animate-spin text-white" /> : <Send size={13} className="text-white" />}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [incident, setIncident] = useState<Incident | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch('/api/incidents')
        const d = await r.json()
        const found = (d.incidents || []).find((i: Incident) => i.id === id)
        if (found) setIncident(found)
        else setNotFound(true)
      } finally { setLoading(false) }
    }
    load()
    const interval = setInterval(load, 8000)
    return () => clearInterval(interval)
  }, [id])

  if (loading) return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  )

  if (notFound || !incident) return (
    <div className="p-6 flex flex-col items-center justify-center min-h-64 gap-4">
      <div className="text-4xl opacity-20">🔍</div>
      <div className="text-dim font-semibold">Incident not found</div>
      <Link href="/incidents" className="btn-primary text-sm">← Back to incidents</Link>
    </div>
  )

  const diff = buildDiff(incident.action_taken || '')
  const resTime = fmtDuration(incident.created_at, incident.resolved_at)

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">

      {/* Back + breadcrumb */}
      <div className="flex items-center gap-3 mb-6 animate-fade-up">
        <Link href="/incidents" className="btn-ghost text-xs">
          <ArrowLeft size={14} /> Back
        </Link>
        <span className="text-slate-3 text-xs">/</span>
        <span className="text-xs font-mono text-slate-3">Incident</span>
        <span className="text-slate-3 text-xs">/</span>
        <span className="text-xs font-mono text-blue">{incident.id}</span>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        {/* LEFT COLUMN */}
        <div className="space-y-5">

          {/* Hero */}
          <div className="rounded-xl bg-gradient-to-br from-ink-2 to-ink-3 border border-ink-4 p-6
                          relative overflow-hidden animate-fade-up">
            <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-10 pointer-events-none"
              style={{ background: 'radial-gradient(circle, #2563eb, transparent)', transform: 'translate(30%,-30%)' }} />
            <div className="font-mono text-[10px] text-slate-3 tracking-widest mb-2">
              INCIDENT · {incident.id.toUpperCase()}
            </div>
            <h1 className="font-display text-2xl font-700 text-dim-2 tracking-tight mb-3">
              {incident.alert_name}
            </h1>
            <div className="flex flex-wrap gap-2 mb-4">
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
              <span className="badge bg-ink-4 text-slate-3 border border-ink-4 font-mono">
                📦 {incident.namespace}/{incident.pod_name}
              </span>
              {incident.resolved_at && (
                <span className="badge bg-ink-4 text-green border border-green/20 font-mono">
                  ⏱ Resolved in {resTime}
                </span>
              )}
            </div>
            {/* Metric row */}
            <div className="grid grid-cols-3 gap-3 mt-4">
              {[
                { label: 'Time to Resolve', value: resTime, color: '#2563eb' },
                { label: 'Severity', value: incident.severity, color: incident.severity === 'critical' ? '#dc2626' : '#d97706' },
                { label: 'Created', value: fmtTime(incident.created_at), color: '#7c3aed' },
              ].map(m => (
                <div key={m.label} className="bg-ink-3 border border-ink-4 rounded-lg p-3 text-center">
                  <div className="font-mono font-600 text-sm uppercase" style={{ color: m.color }}>{m.value}</div>
                  <div className="text-[10px] text-slate-3 mt-1">{m.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Timeline */}
          <div className="card p-5 animate-fade-up" style={{ animationDelay: '60ms' }}>
            <div className="section-title">🔗 Agent Action Timeline</div>
            <div className="space-y-0">
              <TimelineStep icon="📡" label="Alert Trigger" color="#0891b2" tag="ALERT" tagColor="#0891b2"
                time={fmtTime(incident.created_at)}>
                <p className="text-sm text-slate-3 leading-relaxed">
                  Alert <strong className="text-dim">{incident.alert_name}</strong> fired for pod{' '}
                  <code className="bg-ink-3 px-1 rounded text-xs font-mono text-blue-mid">{incident.pod_name}</code>{' '}
                  in namespace <code className="bg-ink-3 px-1 rounded text-xs font-mono text-blue-mid">{incident.namespace}</code>{' '}
                  with severity <strong className="text-dim">{incident.severity}</strong>.
                </p>
              </TimelineStep>

              <TimelineStep icon="🖥️" label="Supervisor Agent" color="#2563eb" tag="COLLECT" tagColor="#2563eb"
                time={fmtTime(incident.created_at)}>
                <p className="text-sm text-slate-3 leading-relaxed mb-2">
                  Resolved pod name, fetched last 80 log lines, created Incident object,
                  pushed to Evaluator queue via Redis.
                </p>
                {incident.raw_logs && (
                  <div className="bg-ink-3 border border-ink-4 rounded-lg p-3 font-mono text-[10px] text-slate-3 max-h-24 overflow-y-auto">
                    {incident.raw_logs.slice(0, 300)}{incident.raw_logs.length > 300 ? '\n...' : ''}
                  </div>
                )}
              </TimelineStep>

              <TimelineStep icon="🧠" label="Evaluator Agent" color="#7c3aed" tag="AI ANALYSIS" tagColor="#7c3aed">
                <p className="text-sm text-slate-3 leading-relaxed mb-2">
                  Sent logs to <strong className="text-dim">Groq Llama 3.3 70B</strong>. Received structured JSON diagnosis.
                </p>
                {incident.ai_diagnosis && (
                  <div className="bg-purple/8 border border-purple/20 rounded-lg p-3 text-sm text-dim leading-relaxed">
                    <div className="text-[10px] font-mono font-semibold text-purple mb-1.5 tracking-wider">AI DIAGNOSIS</div>
                    {incident.ai_diagnosis}
                  </div>
                )}
                {incident.recommended_action && (
                  <div className="bg-blue/8 border border-blue/20 rounded-lg p-3 mt-2 text-sm text-dim leading-relaxed">
                    <div className="text-[10px] font-mono font-semibold text-blue mb-1.5 tracking-wider">RECOMMENDED ACTION</div>
                    {incident.recommended_action}
                  </div>
                )}
              </TimelineStep>

              <TimelineStep icon="🔧" label="Resolver Agent" color="#059669" tag="EXECUTE" tagColor="#059669"
                time={incident.resolved_at ? fmtTime(incident.resolved_at) : undefined}>
                <p className="text-sm text-slate-3 leading-relaxed mb-2">
                  Keyword inference selected action type. Executed real Kubernetes API call.
                </p>
                {incident.action_taken && (
                  <div className="bg-green/8 border border-green/20 rounded-lg p-3 text-sm font-mono text-green leading-relaxed">
                    {incident.action_taken}
                  </div>
                )}
              </TimelineStep>
            </div>
          </div>

          {/* Diff */}
          {diff.length > 0 && (
            <div className="card p-5 animate-fade-up" style={{ animationDelay: '120ms' }}>
              <div className="section-title">⚡ Before / After — Kubernetes State Change</div>
              <DiffView diff={diff} />
            </div>
          )}

          {/* Logs */}
          <div className="card p-5 animate-fade-up" style={{ animationDelay: '160ms' }}>
            <div className="section-title">📋 Raw Pod Logs</div>
            <LogTerminal logs={incident.raw_logs} />
          </div>

          {/* Full JSON */}
          <div className="card p-5 animate-fade-up" style={{ animationDelay: '200ms' }}>
            <div className="section-title">🗂 Full Incident Record (JSON)</div>
            <div className="rounded-lg overflow-hidden border border-ink-4">
              <div className="bg-ink-3 px-4 py-2 text-xs font-mono text-slate-3 border-b border-ink-4">
                store:incidents:{incident.id}
              </div>
              <pre className="bg-[#0a0f1a] p-4 text-[11px] font-mono text-blue-mid
                              overflow-x-auto max-h-64 overflow-y-auto leading-6">
                {JSON.stringify(incident, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN — Chat */}
        <div className="xl:sticky xl:top-14 xl:h-[calc(100vh-3.5rem)] animate-fade-in"
          style={{ animationDelay: '100ms' }}>
          <ChatPanel incident={incident} />
        </div>
      </div>
    </div>
  )
}
