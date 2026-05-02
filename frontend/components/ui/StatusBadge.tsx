import { STATUS_CONFIG } from '@/lib/utils'

interface Props { status: string }

export default function StatusBadge({ status }: Props) {
  const cfg = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] ||
    { color: 'text-slate-3', bg: 'bg-ink-3', label: status, icon: '○' }
  return (
    <span className={`badge ${cfg.color} ${cfg.bg}`}>
      {cfg.icon} {cfg.label}
    </span>
  )
}
