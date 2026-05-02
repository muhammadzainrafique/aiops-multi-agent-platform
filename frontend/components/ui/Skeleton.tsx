
export default function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-ink-3 rounded-lg animate-shimmer
      [background:linear-gradient(90deg,#152236_25%,#1e3050_50%,#152236_75%)]
      [background-size:400px_100%] ${className}`} />
  )
}
