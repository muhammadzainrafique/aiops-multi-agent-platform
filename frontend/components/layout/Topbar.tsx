'use client'
import { useEffect, useState } from 'react'
import { RefreshCw, Wifi, WifiOff } from 'lucide-react'

interface Props { onRefresh?: () => void }

export default function Topbar({ onRefresh }: Props) {
  const [time, setTime] = useState('')
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    }))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch('/api/health')
        const d = await r.json()
        setOnline(d.status === 'healthy')
      } catch { setOnline(false) }
    }
    check()
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="h-14 bg-ink-2/80 backdrop-blur border-b border-ink-4
                       flex items-center justify-between px-6 sticky top-0 z-20">
      <div className="text-xs font-mono text-slate-3">
        AIOps Multi-Agent Platform — Autonomous Kubernetes Operations
      </div>
      <div className="flex items-center gap-4">
        <span className="font-mono text-xs text-slate-3">{time}</span>

        {online !== null && (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold font-mono
            ${online
              ? 'bg-green/10 border border-green/30 text-green'
              : 'bg-red/10 border border-red/30 text-red'}`}>
            <div className={`w-1.5 h-1.5 rounded-full animate-pulse-dot
              ${online ? 'bg-green' : 'bg-red'}`} />
            {online ? 'HEALTHY' : 'OFFLINE'}
          </div>
        )}

        <button onClick={onRefresh}
          className="w-8 h-8 rounded-lg bg-ink-3 border border-ink-4
                     flex items-center justify-center
                     hover:border-blue/40 hover:bg-blue/10 transition-all">
          <RefreshCw size={13} className="text-slate-3" />
        </button>
      </div>
    </header>
  )
}
