import type { Job } from '../api/client'

const STATUS_COLORS: Record<string, string> = {
  new:       'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  reviewed:  'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
  dismissed: 'bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400',
  applied:   'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  interview: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  rejected:  'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  offer:     'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 70 ? 'text-emerald-700 dark:text-emerald-400' : pct >= 40 ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'
  return <span className={`font-bold text-sm ${color}`}>{pct}%</span>
}

interface Props {
  job: Job
  selected?: boolean
  onClick?: () => void
}

export default function JobCard({ job, selected, onClick }: Props) {
  return (
    <div
      onClick={onClick}
      className={`p-3 rounded-xl border cursor-pointer transition-all ${
        selected
          ? 'border-amber-400 bg-amber-50/80 dark:bg-amber-900/20 dark:border-amber-500/60 shadow-sm'
          : 'border-slate-200/70 dark:border-zinc-700/60 bg-white/75 dark:bg-zinc-900/60 backdrop-blur-sm hover:border-amber-300/60 dark:hover:border-amber-500/40 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-sm text-slate-900 dark:text-slate-100 truncate">{job.title || 'Untitled'}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{job.company}{job.location ? ` · ${job.location}` : ''}</p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className={`px-1.5 py-0.5 rounded-md text-xs font-medium ${STATUS_COLORS[job.status] ?? 'bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400'}`}>
            {job.status}
          </span>
          <ScoreBadge score={job.match_score} />
        </div>
      </div>
      {job.skills_required.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {job.skills_required.slice(0, 4).map((s) => (
            <span key={s} className="tag-neutral">{s}</span>
          ))}
          {job.skills_required.length > 4 && (
            <span className="text-xs text-slate-400 dark:text-zinc-500">+{job.skills_required.length - 4}</span>
          )}
        </div>
      )}
    </div>
  )
}
