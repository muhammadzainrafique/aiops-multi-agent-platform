import { LucideIcon } from 'lucide-react'

interface Props {
  label:   string
  value:   string | number
  sub?:    string
  icon:    LucideIcon
  color:   string
  delay?:  number
  glow?:   string
}

export default function StatCard({ label, value, sub, icon: Icon, color, delay = 0, glow }: Props) {
  return (
    <div className="card p-6 animate-fade-up hover:translate-y-[-2px] transition-transform duration-200 relative overflow-hidden"
      style={{ animationDelay: `${delay}ms` }}>
      <div className="absolute top-0 right-0 w-20 h-20 rounded-full opacity-10 pointer-events-none"
        style={{ background: `radial-gradient(circle, ${color}, transparent)`, transform: 'translate(30%,-30%)' }} />
      <div className="flex items-center justify-between mb-4">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center border"
          style={{ background: `${color}15`, borderColor: `${color}30` }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
      <div className="text-3xl font-display font-700 tracking-tight mb-1" style={{ color }}>
        {value}
      </div>
      <div className="text-sm font-medium text-dim">{label}</div>
      {sub && <div className="text-xs text-slate-3 mt-1">{sub}</div>}
    </div>
  )
}
