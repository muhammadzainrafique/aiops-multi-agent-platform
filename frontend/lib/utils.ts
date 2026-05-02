import { type ClassValue, clsx } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return inputs.filter(Boolean).join(' ')
}

export function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

export function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

export function fmtDuration(start: string, end: string | null): string {
  if (!end) return '—'
  const sec = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000)
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m ${sec % 60}s`
}

export const SEV_CONFIG = {
  critical: { color: 'text-red',   bg: 'bg-red-soft/20',    border: 'border-red/30',    dot: '#dc2626', label: 'CRITICAL' },
  warning:  { color: 'text-amber', bg: 'bg-amber-soft/20',  border: 'border-amber/30',  dot: '#d97706', label: 'WARNING'  },
  info:     { color: 'text-blue',  bg: 'bg-blue-soft/20',   border: 'border-blue/30',   dot: '#2563eb', label: 'INFO'     },
} as const

export const STATUS_CONFIG = {
  resolved:           { color: 'text-green',  bg: 'bg-green-soft/20',  label: 'RESOLVED',   icon: '✓' },
  open:               { color: 'text-amber',  bg: 'bg-amber-soft/20',  label: 'OPEN',       icon: '○' },
  in_progress:        { color: 'text-blue',   bg: 'bg-blue-soft/20',   label: 'ACTIVE',     icon: '◎' },
  evaluated:          { color: 'text-purple', bg: 'bg-purple-soft/20', label: 'EVALUATED',  icon: '◈' },
  evaluation_failed:  { color: 'text-red',    bg: 'bg-red-soft/20',    label: 'AI FAILED',  icon: '✗' },
  resolution_failed:  { color: 'text-red',    bg: 'bg-red-soft/20',    label: 'RES FAILED', icon: '✗' },
} as const

export function colorizeLog(line: string): string {
  if (/error|fatal|fail|killed|refused|exception|oom/i.test(line)) return 'log-error'
  if (/warn|warning|stress|pressure|allocated/i.test(line))         return 'log-warn'
  if (/info|start|listen|ready|connected/i.test(line))              return 'log-info'
  if (/success|ok|healthy|resolved/i.test(line))                    return 'log-ok'
  return 'log-dim'
}

export function buildDiff(actionTaken: string) {
  if (actionTaken.includes('RESOURCES PATCHED')) return [
    { type: 'header', text: 'resources.limits — Deployment patch by Resolver Agent' },
    { type: 'ctx',    text: 'spec.template.spec.containers[0].resources:' },
    { type: 'del',    text: '  limits.memory:   128Mi' },
    { type: 'del',    text: '  limits.cpu:      100m'  },
    { type: 'del',    text: '  requests.memory: 64Mi'  },
    { type: 'del',    text: '  requests.cpu:    50m'   },
    { type: 'add',    text: '  limits.memory:   512Mi' },
    { type: 'add',    text: '  limits.cpu:      500m'  },
    { type: 'add',    text: '  requests.memory: 256Mi' },
    { type: 'add',    text: '  requests.cpu:    250m'  },
  ]
  if (actionTaken.includes('SCALED')) return [
    { type: 'header', text: 'spec.replicas — Scale-up by Resolver Agent' },
    { type: 'del',    text: '  spec.replicas: 1' },
    { type: 'add',    text: '  spec.replicas: 3' },
  ]
  if (actionTaken.includes('RESTARTED') || actionTaken.includes('ROLLING RESTART')) return [
    { type: 'header', text: 'Pod lifecycle — Restart executed by Resolver Agent' },
    { type: 'del',    text: '  pod: [CrashLoopBackOff / Error / OOMKilled]' },
    { type: 'add',    text: '  pod: [Deleted → Recreated by ReplicaSet → Running]' },
  ]
  if (actionTaken.includes('NETWORK RESET')) return [
    { type: 'header', text: 'NetworkPolicy — Created by Resolver Agent' },
    { type: 'del',    text: '  NetworkPolicy: none (default-deny)' },
    { type: 'add',    text: '  NetworkPolicy: aiops-allow-all' },
    { type: 'add',    text: '  spec.ingress: [{}]  # allow all' },
    { type: 'add',    text: '  spec.egress:  [{}]  # allow all' },
  ]
  if (actionTaken.includes('ROLLBACK')) return [
    { type: 'header', text: 'Deployment — Rollback triggered by Resolver Agent' },
    { type: 'del',    text: '  restartedAt: (none)' },
    { type: 'add',    text: `  restartedAt: ${new Date().toISOString()}` },
    { type: 'add',    text: '  aiops/rollback-triggered: "true"' },
  ]
  return []
}
