'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Activity, CheckCircle2, AlertTriangle, XCircle,
  RefreshCw, Zap, Server, Brain, Wrench, Shield,
  Clock, TrendingUp, ChevronDown, ChevronUp,
  ArrowRight, Circle, Cpu, Database, GitBranch,
  BarChart2, Eye, AlertCircle
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie,
  Cell, Legend
} from 'recharts';

// ── Types ────────────────────────────────────────────────────────────────────
interface Incident {
  id: string; alert_name: string; namespace: string; pod_name: string;
  severity: string; status: string; ai_diagnosis: string;
  recommended_action: string; action_taken: string;
  raw_logs: string; created_at: string; resolved_at: string | null;
}
interface ChartPt { time: string; total: number; resolved: number; open: number; }

// ── Constants ─────────────────────────────────────────────────────────────────
const ALERTS = [
  { label: 'Pod Crash Loop', value: 'PodCrashLooping', sev: 'critical' },
  { label: 'High Memory Usage', value: 'HighMemoryUsage', sev: 'warning' },
  { label: 'Pod Not Ready', value: 'PodNotReady', sev: 'warning' },
  { label: 'High CPU Usage', value: 'HighCPUUsage', sev: 'warning' },
  { label: 'Deployment Unavailable', value: 'DeploymentUnavailable', sev: 'critical' },
];

const SEV_CFG: Record<string, { color: string; bg: string; border: string; dot: string }> = {
  critical: { color: '#dc2626', bg: '#fee2e2', border: '#fca5a5', dot: '#ef4444' },
  warning: { color: '#d97706', bg: '#fef3c7', border: '#fcd34d', dot: '#f59e0b' },
  info: { color: '#2563eb', bg: '#dbeafe', border: '#93c5fd', dot: '#3b82f6' },
};

const STATUS_CFG: Record<string, { color: string; bg: string; label: string }> = {
  resolved: { color: '#059669', bg: '#d1fae5', label: 'Resolved' },
  open: { color: '#d97706', bg: '#fef3c7', label: 'Open' },
  in_progress: { color: '#2563eb', bg: '#dbeafe', label: 'In Progress' },
  evaluated: { color: '#7c3aed', bg: '#ede9fe', label: 'Evaluated' },
  evaluation_failed: { color: '#dc2626', bg: '#fee2e2', label: 'Eval Failed' },
  resolution_failed: { color: '#dc2626', bg: '#fee2e2', label: 'Res. Failed' },
};

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
function fmtFull(iso: string) {
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function dur(start: string, end: string | null) {
  if (!end) return null;
  const s = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000);
  return s < 60 ? `${s}s` : `${Math.round(s / 60)}m ${s % 60}s`;
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, icon: Icon, accent, delay = 0 }:
  { label: string; value: string | number; sub?: string; icon: any; accent: string; delay?: number }) {
  return (
    <div className="card card-lift p-6 anim-fade-up" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: `${accent}18`, border: `1px solid ${accent}30` }}>
          <Icon size={18} style={{ color: accent }} />
        </div>
        <TrendingUp size={14} style={{ color: 'var(--text-4)' }} />
      </div>
      <div className="text-3xl font-bold tracking-tight mb-1" style={{ color: 'var(--text-1)', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
      <div className="text-sm font-medium" style={{ color: 'var(--text-2)' }}>{label}</div>
      {sub && <div className="text-xs mt-1" style={{ color: 'var(--text-4)' }}>{sub}</div>}
    </div>
  );
}

// ── Pipeline Visualiser ───────────────────────────────────────────────────────
function Pipeline({ online }: { online: boolean }) {
  const nodes = [
    { icon: Activity, label: 'Prometheus', sub: 'Alert Source', color: '#0891b2' },
    { icon: Server, label: 'Supervisor', sub: 'Webhook · Logs', color: '#2563eb' },
    { icon: Brain, label: 'Evaluator', sub: 'Groq LLM · AI', color: '#7c3aed' },
    { icon: Wrench, label: 'Resolver', sub: 'K8s Remediation', color: '#059669' },
  ];
  return (
    <div className="card p-6 anim-fade-up" style={{ animationDelay: '100ms' }}>
      <div className="flex items-center gap-2 mb-6">
        <GitBranch size={15} style={{ color: 'var(--blue)' }} />
        <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: 'var(--text-3)' }}>
          Agent Pipeline
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full anim-pulse-dot"
            style={{ background: online ? 'var(--green)' : 'var(--red)' }} />
          <span className="text-xs font-mono" style={{ color: online ? 'var(--green)' : 'var(--red)' }}>
            {online ? 'All Systems Operational' : 'System Offline'}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-0">
        {nodes.map((n, i) => (
          <div key={n.label} className="flex items-center flex-1">
            <div className="flex flex-col items-center flex-1">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-2 shadow-sm"
                style={{ background: `${n.color}12`, border: `2px solid ${n.color}30` }}>
                <n.icon size={20} style={{ color: n.color }} />
              </div>
              <div className="text-xs font-semibold text-center" style={{ color: 'var(--text-1)' }}>{n.label}</div>
              <div className="text-xs text-center mt-0.5" style={{ color: 'var(--text-4)' }}>{n.sub}</div>
              <div className="w-2 h-2 rounded-full mt-2 anim-pulse-dot"
                style={{ background: online ? n.color : '#cbd5e1', animationDelay: `${i * 400}ms` }} />
            </div>
            {i < nodes.length - 1 && (
              <div className="flex items-center mb-8 flex-shrink-0 w-8">
                <div className="h-0.5 w-full" style={{ background: `linear-gradient(90deg, ${nodes[i].color}, ${nodes[i + 1].color})` }} />
                <ArrowRight size={12} style={{ color: nodes[i + 1].color, marginLeft: -4, flexShrink: 0 }} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Incident Row ──────────────────────────────────────────────────────────────
function IncidentRow({ inc, idx, isNew }: { inc: Incident; idx: number; isNew: boolean }) {
  const [open, setOpen] = useState(false);
  const sev = SEV_CFG[inc.severity] || SEV_CFG.info;
  const status = STATUS_CFG[inc.status] || { color: '#64748b', bg: '#f1f5f9', label: inc.status };
  const resTime = dur(inc.created_at, inc.resolved_at);

  return (
    <div className={`anim-slide-r ${isNew ? 'anim-new-row' : ''}`}
      style={{ animationDelay: `${idx * 50}ms` }}>
      <div
        className="card mb-2 cursor-pointer overflow-hidden transition-all"
        style={{ borderLeft: `3px solid ${sev.dot}` }}
        onClick={() => setOpen(o => !o)}>
        {/* ── Collapsed row ── */}
        <div className="px-4 py-3 flex items-center gap-3">
          {/* Severity badge */}
          <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded flex-shrink-0"
            style={{ background: sev.bg, color: sev.color, border: `1px solid ${sev.border}` }}>
            {(inc.severity || 'info').toUpperCase()}
          </span>

          {/* Alert name + pod */}
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-sm" style={{ color: 'var(--text-1)' }}>{inc.alert_name}</div>
            <div className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-3)' }}>
              {inc.namespace}/{inc.pod_name}
            </div>
          </div>

          {/* AI badge if diagnosis exists */}
          {inc.ai_diagnosis && (
            <div className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded text-xs flex-shrink-0"
              style={{ background: '#ede9fe', color: '#7c3aed', border: '1px solid #c4b5fd' }}>
              <Brain size={10} /> AI Diagnosed
            </div>
          )}

          {/* Resolution time */}
          {resTime && (
            <div className="hidden md:flex items-center gap-1 text-xs flex-shrink-0"
              style={{ color: 'var(--text-4)' }}>
              <Clock size={10} /> {resTime}
            </div>
          )}

          {/* Status */}
          <span className="text-xs font-medium px-2.5 py-1 rounded-full flex-shrink-0"
            style={{ background: status.bg, color: status.color }}>
            {status.label}
          </span>

          {/* Time */}
          <span className="text-xs font-mono flex-shrink-0" style={{ color: 'var(--text-4)' }}>
            {fmtTime(inc.created_at)}
          </span>

          <div style={{ color: 'var(--text-4)' }}>
            {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        </div>

        {/* ── Expanded detail ── */}
        {open && (
          <div className="border-t px-4 pb-5 pt-4 space-y-4 anim-fade-in"
            style={{ borderColor: 'var(--border)', background: 'var(--surface-2)' }}>

            {/* Meta row */}
            <div className="flex flex-wrap gap-4 text-xs font-mono pb-3"
              style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-3)' }}>
              <span><span style={{ color: 'var(--text-4)' }}>ID:</span> {inc.id}</span>
              <span><span style={{ color: 'var(--text-4)' }}>Created:</span> {fmtFull(inc.created_at)}</span>
              {inc.resolved_at && <span><span style={{ color: 'var(--text-4)' }}>Resolved:</span> {fmtFull(inc.resolved_at)}</span>}
              {resTime && <span><span style={{ color: 'var(--text-4)' }}>Duration:</span> {resTime}</span>}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* AI Diagnosis */}
              {inc.ai_diagnosis && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Brain size={12} style={{ color: '#7c3aed' }} />
                    <span className="text-xs font-semibold tracking-wider uppercase" style={{ color: '#7c3aed' }}>
                      AI Diagnosis (Groq LLM)
                    </span>
                  </div>
                  <div className="text-sm leading-relaxed p-3 rounded-lg"
                    style={{ background: '#faf5ff', border: '1px solid #e9d5ff', color: 'var(--text-2)' }}>
                    {inc.ai_diagnosis}
                  </div>
                </div>
              )}

              {/* Recommended Action */}
              {inc.recommended_action && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <AlertCircle size={12} style={{ color: '#2563eb' }} />
                    <span className="text-xs font-semibold tracking-wider uppercase" style={{ color: '#2563eb' }}>
                      Recommended Action
                    </span>
                  </div>
                  <div className="text-sm leading-relaxed p-3 rounded-lg"
                    style={{ background: '#eff6ff', border: '1px solid #bfdbfe', color: 'var(--text-2)' }}>
                    {inc.recommended_action}
                  </div>
                </div>
              )}
            </div>

            {/* Action Taken */}
            {inc.action_taken && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <Wrench size={12} style={{ color: '#059669' }} />
                  <span className="text-xs font-semibold tracking-wider uppercase" style={{ color: '#059669' }}>
                    Resolver Action Taken
                  </span>
                </div>
                <div className="text-sm leading-relaxed p-3 rounded-lg font-mono"
                  style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#065f46' }}>
                  {inc.action_taken}
                </div>
              </div>
            )}

            {/* Raw Logs */}
            {inc.raw_logs && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <Eye size={12} style={{ color: 'var(--text-3)' }} />
                  <span className="text-xs font-semibold tracking-wider uppercase" style={{ color: 'var(--text-3)' }}>
                    Raw Pod Logs
                  </span>
                </div>
                <pre className="text-xs font-mono p-3 rounded-lg overflow-x-auto leading-relaxed"
                  style={{ background: '#0f172a', color: '#94a3b8', border: '1px solid #1e293b' }}>
                  {inc.raw_logs}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────────
function ChartTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="card p-3 text-xs" style={{ boxShadow: 'var(--shadow-lg)' }}>
      <div className="font-mono mb-1" style={{ color: 'var(--text-3)' }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="font-medium" style={{ color: p.color }}>{p.name}: {p.value}</div>
      ))}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ════════════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [chart, setChart] = useState<ChartPt[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [alertSel, setAlertSel] = useState(ALERTS[0].value);
  const [triggering, setTriggering] = useState(false);
  const [trigMsg, setTrigMsg] = useState('');
  const [filter, setFilter] = useState('all');
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const prevIds = useRef<Set<string>>(new Set());

  const fetchAll = useCallback(async () => {
    try {
      const [incRes, hlRes] = await Promise.all([
        fetch('/api/incidents'), fetch('/api/health'),
      ]);
      const incData = await incRes.json();
      const hlData = await hlRes.json();
      const list: Incident[] = (incData.incidents || []);

      // Detect new incidents
      const incoming = new Set(list.map((i: Incident) => i.id));
      const fresh = new Set([...incoming].filter(id => !prevIds.current.has(id)));
      if (fresh.size > 0) {
        setNewIds(fresh);
        setTimeout(() => setNewIds(new Set()), 2500);
      }
      prevIds.current = incoming;

      setIncidents(list);
      setHealth(hlData);
      setLastRefresh(new Date());

      const now = new Date();
      const total = list.length;
      const resolved = list.filter((i: Incident) => i.status === 'resolved').length;
      const open = list.filter((i: Incident) => ['open', 'in_progress'].includes(i.status)).length;
      setChart(p => [...p, {
        time: now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        total, resolved, open,
      }].slice(-14));
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, 8000);
    const onKey = (e: KeyboardEvent) => { if (e.key === 'r' || e.key === 'R') fetchAll(); };
    window.addEventListener('keydown', onKey);
    return () => { clearInterval(id); window.removeEventListener('keydown', onKey); };
  }, [fetchAll]);

  const fireAlert = async () => {
    setTriggering(true); setTrigMsg('');
    const a = ALERTS.find(x => x.value === alertSel)!;
    try {
      const r = await fetch('/api/trigger', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alertname: a.value, namespace: 'default', pod: 'crash-test', severity: a.sev }),
      });
      const d = await r.json();
      setTrigMsg(d.processed ? `✓ ${d.processed} incident dispatched — pipeline processing` : '⚠ No incidents returned');
      setTimeout(fetchAll, 3000);
      setTimeout(fetchAll, 7000);
    } catch { setTrigMsg('✗ Cannot reach Supervisor'); }
    finally { setTriggering(false); }
  };

  // Derived stats
  const total = incidents.length;
  const resolved = incidents.filter(i => i.status === 'resolved').length;
  const open = incidents.filter(i => ['open', 'in_progress'].includes(i.status)).length;
  const failed = incidents.filter(i => i.status?.includes('failed')).length;
  const avgRes = (() => {
    const times = incidents
      .filter(i => i.resolved_at)
      .map(i => (new Date(i.resolved_at!).getTime() - new Date(i.created_at).getTime()) / 1000);
    if (!times.length) return null;
    const avg = times.reduce((a, b) => a + b, 0) / times.length;
    return avg < 60 ? `${avg.toFixed(0)}s` : `${(avg / 60).toFixed(1)}m`;
  })();
  const isOnline = health?.status === 'healthy';

  // Pie data
  const pieData = [
    { name: 'Resolved', value: resolved, color: '#059669' },
    { name: 'Open', value: open, color: '#d97706' },
    { name: 'Failed', value: failed, color: '#dc2626' },
  ].filter(d => d.value > 0);

  // Filtered incidents
  const filtered = filter === 'all' ? incidents
    : filter === 'open' ? incidents.filter(i => ['open', 'in_progress'].includes(i.status))
      : incidents.filter(i => i.status === filter);

  // Severity counts for mini bars
  const critCount = incidents.filter(i => i.severity === 'critical').length;
  const warnCount = incidents.filter(i => i.severity === 'warning').length;

  return (
    <div className="min-h-screen" style={{ background: 'var(--surface-2)' }}>

      {/* ── SIDEBAR ──────────────────────────────────────────────────────────── */}
      <aside className="fixed left-0 top-0 bottom-0 w-16 flex flex-col items-center py-5 gap-5 z-40"
        style={{ background: 'var(--navy)', borderRight: '1px solid #1e3a5f' }}>
        {/* Logo */}
        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: 'rgba(59,130,246,0.2)', border: '1px solid rgba(59,130,246,0.4)' }}>
          <Shield size={18} color="#93c5fd" />
        </div>
        <div className="w-full h-px" style={{ background: '#1e3a5f' }} />
        {[
          { icon: BarChart2, active: true, tip: 'Dashboard' },
          { icon: Activity, active: false, tip: 'Monitoring' },
          { icon: Database, active: false, tip: 'Storage' },
          { icon: Cpu, active: false, tip: 'Compute' },
        ].map(({ icon: Icon, active, tip }) => (
          <div key={tip} className="w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer transition-all"
            title={tip}
            style={{
              background: active ? 'rgba(59,130,246,0.25)' : 'transparent',
              border: `1px solid ${active ? 'rgba(59,130,246,0.5)' : 'transparent'}`,
            }}>
            <Icon size={16} color={active ? '#93c5fd' : '#4a6fa0'} />
          </div>
        ))}
        {/* Status dot at bottom */}
        <div className="mt-auto flex flex-col items-center gap-1">
          <div className="w-2 h-2 rounded-full anim-pulse-dot"
            style={{ background: isOnline ? '#22c55e' : '#ef4444' }} />
          <span className="text-xs" style={{ color: '#4a6fa0', fontSize: 9, fontFamily: 'DM Mono' }}>
            {isOnline ? 'ON' : 'OFF'}
          </span>
        </div>
      </aside>

      {/* ── MAIN ─────────────────────────────────────────────────────────────── */}
      <div style={{ marginLeft: 64 }}>

        {/* ── TOP BAR ── */}
        <header className="sticky top-0 z-30 px-6 py-3 flex items-center justify-between"
          style={{ background: 'rgba(248,250,252,0.92)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--border)' }}>
          <div>
            <h1 className="font-display text-lg font-bold" style={{ color: 'var(--navy)' }}>
              AIOps Operations Centre
            </h1>
            <p className="text-xs" style={{ color: 'var(--text-3)' }}>
              Autonomous Multi-Agent IT Operations Platform — FYP 2026
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Keyboard hint */}
            <span className="hidden md:block text-xs font-mono px-2 py-1 rounded"
              style={{ background: 'var(--surface-3)', color: 'var(--text-4)', border: '1px solid var(--border)' }}>
              Press R to refresh
            </span>
            {/* Last refresh */}
            <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-3)' }}>
              <Clock size={12} />
              <span className="font-mono">{lastRefresh.toLocaleTimeString()}</span>
            </div>
            {/* System status pill */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full"
              style={{
                background: isOnline ? '#d1fae5' : '#fee2e2',
                border: `1px solid ${isOnline ? '#a7f3d0' : '#fca5a5'}`,
              }}>
              <div className="w-1.5 h-1.5 rounded-full anim-pulse-dot"
                style={{ background: isOnline ? '#059669' : '#dc2626' }} />
              <span className="text-xs font-semibold" style={{ color: isOnline ? '#065f46' : '#991b1b' }}>
                {isOnline ? 'Healthy' : 'Offline'}
              </span>
            </div>
            <button onClick={fetchAll}
              className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:scale-105"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
              <RefreshCw size={13} style={{ color: 'var(--text-3)' }} />
            </button>
          </div>
        </header>

        <main className="p-6 space-y-5 max-w-screen-xl">

          {/* ── STAT CARDS ── */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard label="Total Incidents" value={loading ? '—' : total} icon={Activity} accent="#2563eb" delay={0}
              sub={`${incidents.filter(i => i.severity === 'critical').length} critical`} />
            <StatCard label="Resolved" value={loading ? '—' : resolved} icon={CheckCircle2} accent="#059669" delay={60}
              sub={total > 0 ? `${Math.round(resolved / total * 100)}% resolution rate` : 'No data yet'} />
            <StatCard label="Open / Active" value={loading ? '—' : open} icon={AlertTriangle} accent="#d97706" delay={120}
              sub={open > 0 ? 'Awaiting remediation' : 'All clear'} />
            <StatCard label="Avg Resolution" value={loading ? '—' : (avgRes || '—')} icon={Clock} accent="#7c3aed" delay={180}
              sub="Mean time to resolve" />
          </div>

          {/* ── PIPELINE ── */}
          <Pipeline online={isOnline} />

          {/* ── MID ROW: Chart + Severity ── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

            {/* Area chart */}
            <div className="lg:col-span-2 card p-5 anim-fade-up" style={{ animationDelay: '200ms' }}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs font-semibold tracking-widest uppercase" style={{ color: 'var(--text-3)' }}>
                    Incident Rate — Live Feed
                  </div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--text-4)' }}>Auto-refreshes every 8 seconds</div>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  {[['Total', '#2563eb'], ['Resolved', '#059669'], ['Open', '#d97706']].map(([n, c]) => (
                    <div key={n} className="flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full" style={{ background: c }} />
                      <span style={{ color: 'var(--text-3)' }}>{n}</span>
                    </div>
                  ))}
                </div>
              </div>
              {chart.length < 2 ? (
                <div className="h-44 flex flex-col items-center justify-center gap-2">
                  <Activity size={24} style={{ color: 'var(--text-4)' }} />
                  <div className="text-xs" style={{ color: 'var(--text-4)' }}>Fire an alert to populate the chart</div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={176}>
                  <AreaChart data={chart} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <defs>
                      {[['t', '#2563eb'], ['r', '#059669'], ['o', '#d97706']].map(([id, c]) => (
                        <linearGradient key={id} id={`g${id}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={c} stopOpacity={0.15} />
                          <stop offset="95%" stopColor={c} stopOpacity={0} />
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'DM Mono' }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'DM Mono' }} allowDecimals={false} />
                    <Tooltip content={<ChartTip />} />
                    <Area type="monotone" dataKey="total" stroke="#2563eb" fill="url(#gt)" strokeWidth={2} dot={false} name="Total" />
                    <Area type="monotone" dataKey="resolved" stroke="#059669" fill="url(#gr)" strokeWidth={2} dot={false} name="Resolved" />
                    <Area type="monotone" dataKey="open" stroke="#d97706" fill="url(#go)" strokeWidth={2} dot={false} name="Open" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Right column: Pie + Severity bars */}
            <div className="space-y-4">

              {/* Pie chart */}
              <div className="card p-4 anim-fade-up" style={{ animationDelay: '250ms' }}>
                <div className="text-xs font-semibold tracking-widest uppercase mb-3" style={{ color: 'var(--text-3)' }}>
                  Status Breakdown
                </div>
                {pieData.length === 0 ? (
                  <div className="h-28 flex items-center justify-center text-xs" style={{ color: 'var(--text-4)' }}>No data</div>
                ) : (
                  <ResponsiveContainer width="100%" height={120}>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius={32} outerRadius={52}
                        paddingAngle={3} dataKey="value">
                        {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                      </Pie>
                      <Tooltip formatter={(v: any, n: any) => [v, n]} />
                      <Legend iconSize={8} wrapperStyle={{ fontSize: 11, fontFamily: 'DM Sans' }} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>

              {/* Severity bars */}
              <div className="card p-4 anim-fade-up" style={{ animationDelay: '300ms' }}>
                <div className="text-xs font-semibold tracking-widest uppercase mb-3" style={{ color: 'var(--text-3)' }}>
                  Severity Distribution
                </div>
                {[
                  { label: 'Critical', count: critCount, color: '#dc2626', bg: '#fee2e2' },
                  { label: 'Warning', count: warnCount, color: '#d97706', bg: '#fef3c7' },
                ].map(({ label, count, color, bg }) => (
                  <div key={label} className="mb-3">
                    <div className="flex justify-between text-xs mb-1">
                      <span style={{ color: 'var(--text-2)', fontWeight: 500 }}>{label}</span>
                      <span className="font-mono font-semibold" style={{ color }}>{count}</span>
                    </div>
                    <div className="h-2 rounded-full" style={{ background: bg }}>
                      <div className="h-2 rounded-full transition-all duration-700"
                        style={{ width: total > 0 ? `${count / total * 100}%` : '0%', background: color }} />
                    </div>
                  </div>
                ))}
                <div className="mt-3 pt-3 flex justify-between text-xs"
                  style={{ borderTop: '1px solid var(--border)', color: 'var(--text-4)' }}>
                  <span>Redis</span>
                  <span className="font-mono" style={{ color: health?.redis === 'ok' ? '#059669' : '#dc2626' }}>
                    {health?.redis || '—'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ── TRIGGER PANEL ── */}
          <div className="card p-4 anim-fade-up" style={{ animationDelay: '350ms', borderColor: '#bfdbfe', background: '#eff6ff' }}>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 flex-shrink-0">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                  style={{ background: '#dbeafe', border: '1px solid #93c5fd' }}>
                  <Zap size={13} style={{ color: '#2563eb' }} />
                </div>
                <div>
                  <div className="text-xs font-semibold" style={{ color: 'var(--navy)' }}>Simulate Alert</div>
                  <div className="text-xs" style={{ color: 'var(--text-3)' }}>Inject test incident into pipeline</div>
                </div>
              </div>

              <select value={alertSel} onChange={e => setAlertSel(e.target.value)}
                className="flex-1 min-w-48 px-3 py-2 rounded-lg text-sm"
                style={{
                  background: 'white', border: '1px solid #93c5fd', color: 'var(--text-1)',
                  outline: 'none', fontFamily: 'DM Sans'
                }}>
                {ALERTS.map(a => (
                  <option key={a.value} value={a.value}>{a.label} — {a.sev}</option>
                ))}
              </select>

              <button onClick={fireAlert} disabled={triggering}
                className="px-5 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all flex-shrink-0"
                style={{
                  background: triggering ? '#93c5fd' : '#2563eb',
                  color: 'white', cursor: triggering ? 'wait' : 'pointer',
                  boxShadow: triggering ? 'none' : '0 2px 8px rgba(37,99,235,0.35)',
                }}>
                {triggering
                  ? <><RefreshCw size={13} className="anim-spin" /> Processing...</>
                  : <><Zap size={13} /> Fire Alert</>}
              </button>

              {trigMsg && (
                <div className="text-xs font-mono px-3 py-1.5 rounded-lg"
                  style={{
                    background: trigMsg.startsWith('✓') ? '#d1fae5' : '#fee2e2',
                    color: trigMsg.startsWith('✓') ? '#065f46' : '#991b1b',
                    border: `1px solid ${trigMsg.startsWith('✓') ? '#a7f3d0' : '#fca5a5'}`,
                  }}>
                  {trigMsg}
                </div>
              )}
            </div>
          </div>

          {/* ── INCIDENT FEED ── */}
          <div className="anim-fade-up" style={{ animationDelay: '400ms' }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-sm" style={{ color: 'var(--text-1)' }}>Incident Feed</h2>
                <span className="text-xs font-mono px-2 py-0.5 rounded-full font-semibold"
                  style={{ background: '#dbeafe', color: '#1d4ed8' }}>{total}</span>
              </div>
              <div className="flex gap-1.5">
                {[
                  { key: 'all', label: 'All' },
                  { key: 'open', label: 'Open' },
                  { key: 'resolved', label: 'Resolved' },
                  { key: 'resolution_failed', label: 'Failed' },
                ].map(f => (
                  <button key={f.key} onClick={() => setFilter(f.key)}
                    className="px-3 py-1 rounded-lg text-xs font-medium transition-all"
                    style={{
                      background: filter === f.key ? 'var(--navy)' : 'var(--surface)',
                      color: filter === f.key ? 'white' : 'var(--text-2)',
                      border: `1px solid ${filter === f.key ? 'var(--navy)' : 'var(--border)'}`,
                      boxShadow: filter === f.key ? 'none' : 'var(--shadow-sm)',
                    }}>
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => <div key={i} className="skeleton h-14 w-full" />)}
              </div>
            ) : filtered.length === 0 ? (
              <div className="card p-16 text-center">
                <Activity size={36} className="mx-auto mb-3" style={{ color: 'var(--text-4)' }} />
                <div className="font-medium mb-1" style={{ color: 'var(--text-2)' }}>No incidents found</div>
                <div className="text-sm" style={{ color: 'var(--text-4)' }}>
                  {filter === 'all' ? 'Fire a test alert above to see the AI pipeline in action' : `No ${filter} incidents`}
                </div>
              </div>
            ) : (
              <div>
                {filtered.map((inc, i) => (
                  <IncidentRow key={inc.id} inc={inc} idx={i} isNew={newIds.has(inc.id)} />
                ))}
              </div>
            )}
          </div>

          {/* ── FOOTER ── */}
          <div className="text-center py-4 text-xs font-mono"
            style={{ color: 'var(--text-4)', borderTop: '1px solid var(--border)' }}>
            AIOps Multi-Agent Platform &nbsp;·&nbsp; Muhammad Zain (FA22-CSE-024) &nbsp;·&nbsp;
            Hamza Maqsood (FA22-CSE-080) &nbsp;·&nbsp; Muhammad Farooq (FA22-CSE-090)
            &nbsp;·&nbsp; MUST 2026 &nbsp;·&nbsp; Supervisor: Engr. Waqas Riaz
          </div>
        </main>
      </div>
    </div>
  );
}
