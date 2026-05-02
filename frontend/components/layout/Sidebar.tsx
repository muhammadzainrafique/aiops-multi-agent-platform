'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, AlertTriangle, Bot,
  BarChart3, Shield, Activity
} from 'lucide-react'

const NAV = [
  { href: '/',           icon: LayoutDashboard, label: 'Dashboard'  },
  { href: '/incidents',  icon: AlertTriangle,   label: 'Incidents'  },
  { href: '/agents',     icon: Bot,             label: 'Agents'     },
  { href: '/analytics',  icon: BarChart3,       label: 'Analytics'  },
]

export default function Sidebar() {
  const path = usePathname()
  return (
    <aside className="w-56 flex-shrink-0 bg-ink-2 border-r border-ink-4
                      flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-ink-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue rounded-lg flex items-center justify-center shadow-glow">
            <Shield size={16} className="text-white" />
          </div>
          <div>
            <div className="font-display font-700 text-sm text-dim-2 tracking-tight">AIOps</div>
            <div className="font-mono text-[9px] text-slate-3 tracking-wider">OPERATIONS CENTRE</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="px-3 mb-3 text-[9px] font-semibold tracking-widest uppercase text-slate-3">
          Navigation
        </p>
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = path === href || (href !== '/' && path.startsWith(href))
          return (
            <Link key={href} href={href}
              className={`nav-link ${active ? 'active' : ''}`}>
              <Icon size={16} />
              <span>{label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-ink-4">
        <div className="flex items-center gap-2 mb-1">
          <Activity size={12} className="text-slate-3" />
          <span className="text-[10px] font-mono text-slate-3">FA22-CSE-024/080/090</span>
        </div>
        <div className="text-[9px] text-slate-font-mono tracking-wide text-slate-4">
          MUST FYP 2026
        </div>
      </div>
    </aside>
  )
}
