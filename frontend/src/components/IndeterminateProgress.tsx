import { useEffect, useState } from 'react'

// Scout/manual-JD analysis is a single opaque LLM call (~15-20s) with no
// natural sub-steps to report real percentages for (unlike Tailor Resume's
// bounded round loop). An indeterminate bar + elapsed-seconds counter is the
// honest way to show "still working, not stuck" without faking a percentage.
export default function IndeterminateProgress({ active, label }: { active: boolean; label: string }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!active) { setElapsed(0); return }
    const start = Date.now()
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 500)
    return () => clearInterval(id)
  }, [active])

  if (!active) return null

  return (
    <div className="mt-3">
      <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-zinc-700 overflow-hidden">
        <div className="h-full w-1/3 rounded-full bg-amber-500 progress-indeterminate" />
      </div>
      <p className="mt-1 text-xs text-slate-400 dark:text-zinc-500">{label} · {elapsed}s</p>
    </div>
  )
}
