import { LucideIcon } from 'lucide-react'

interface Props { icon: LucideIcon; title: string; sub: string }

export default function EmptyState({ icon: Icon, title, sub }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-50">
      <Icon size={40} className="text-slate-3" />
      <div className="text-center">
        <div className="font-semibold text-dim mb-1">{title}</div>
        <div className="text-sm text-slate-3">{sub}</div>
      </div>
    </div>
  )
}
