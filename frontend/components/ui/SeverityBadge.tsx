import { SEV_CONFIG } from '@/lib/utils'

interface Props { severity: string; size?: 'sm' | 'md' }

export default function SeverityBadge({ severity, size = 'md' }: Props) {
  const cfg = SEV_CONFIG[severity as keyof typeof SEV_CONFIG] || SEV_CONFIG.info
  return (
    <span className={`badge ${cfg.color} ${cfg.bg} border ${cfg.border}
      ${size === 'sm' ? 'text-[9px] px-1.5 py-0.5' : ''}`}>
      {cfg.label}
    </span>
  )
}
